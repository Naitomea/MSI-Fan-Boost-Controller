# yamdcc_client.py
from __future__ import annotations

import struct
import time
from dataclasses import dataclass
from typing import Any

import msgpack
import pywintypes
import win32file
import win32pipe


class YAMDCCError(RuntimeError):
    pass


class YAMDCCPipeNotFoundError(YAMDCCError):
    pass


class YAMDCCAccessDeniedError(YAMDCCError):
    pass


class YAMDCCTimeoutError(YAMDCCError):
    pass


@dataclass
class YAMDCCClient:
    server_pipe_name: str = "YAMDCC-Server"
    wait_timeout_ms: int = 3000
    read_timeout: float = 3.0
    connect_delay: float = 0.5

    # YAMDCC IPC constants
    COMMAND_SET_FULL_BLAST: int = 6

    RESPONSE_SUCCESS: int = 1
    RESPONSE_ERROR: int = 2

    @property
    def server_pipe_path(self) -> str:
        return rf"\\.\pipe\{self.server_pipe_name}"

    def is_service_available(self) -> bool:
        """
        Lightweight check used by the UI.

        It only checks whether the main YAMDCC named pipe is available;
        it does not send any fan command.
        """
        try:
            win32pipe.WaitNamedPipe(self.server_pipe_path, min(self.wait_timeout_ms, 500))
            return True
        except pywintypes.error:
            return False

    def set_full_blast(self, enabled: bool) -> bool:
        """
        Active ou désactive le Full Blast / Cooler Boost.

        Returns:
            True si le service confirme le succès.
        """
        return self._send_set_full_blast(1 if enabled else 0)

    def enable_full_blast(self) -> bool:
        return self.set_full_blast(True)

    def disable_full_blast(self) -> bool:
        return self.set_full_blast(False)

    def toggle_full_blast(self) -> bool:
        return self._send_set_full_blast(-1)

    def _send_set_full_blast(self, value: int) -> bool:
        response = self._send_command(
            command=self.COMMAND_SET_FULL_BLAST,
            int_arg=value,
        )

        if response is None:
            raise YAMDCCTimeoutError(
                "Commande envoyée, mais aucune réponse reçue du service YAMDCC."
            )

        response_type, response_values = self._parse_response(response)

        if response_type == self.RESPONSE_SUCCESS:
            return True

        if response_type == self.RESPONSE_ERROR:
            raise YAMDCCError(
                f"Le service YAMDCC a refusé la commande : {response_values!r}"
            )

        raise YAMDCCError(f"Réponse inattendue du service YAMDCC : {response!r}")

    def _send_command(self, command: int, int_arg: int) -> Any:
        data_pipe_name = self._get_data_pipe_name()
        data_pipe_path = self._to_pipe_path(data_pipe_name)

        handle = self._open_pipe(
            data_pipe_path,
            win32file.GENERIC_READ | win32file.GENERIC_WRITE,
        )

        try:
            # Important : laisse le service attacher son handler de réception.
            time.sleep(self.connect_delay)

            self._write_service_command(handle, command, int_arg)

            return self._read_msgpack_object(
                handle,
                timeout=self.read_timeout,
            )

        finally:
            win32file.CloseHandle(handle)

    def _get_data_pipe_name(self) -> str:
        handle = self._open_pipe(
            self.server_pipe_path,
            win32file.GENERIC_READ,
        )

        try:
            data_pipe_name = self._read_msgpack_object(
                handle,
                timeout=self.read_timeout,
            )

            if not isinstance(data_pipe_name, str):
                raise YAMDCCError(f"Nom de pipe inattendu : {data_pipe_name!r}")

            return data_pipe_name

        finally:
            win32file.CloseHandle(handle)

    def _open_pipe(self, path: str, access: int):
        try:
            win32pipe.WaitNamedPipe(path, self.wait_timeout_ms)

            return win32file.CreateFile(
                path,
                access,
                0,
                None,
                win32file.OPEN_EXISTING,
                0,
                None,
            )

        except pywintypes.error as e:
            if e.winerror == 2:
                raise YAMDCCPipeNotFoundError(
                    "Pipe YAMDCC introuvable. Le service YAMDCC ne semble pas lancé."
                ) from e

            if e.winerror == 5:
                raise YAMDCCAccessDeniedError(
                    "Accès refusé au pipe YAMDCC. Lance Python avec les mêmes droits que YAMDCC, probablement en administrateur."
                ) from e

            if e.winerror == 121:
                raise YAMDCCTimeoutError(
                    "Timeout lors de la connexion au pipe YAMDCC."
                ) from e

            raise YAMDCCError(f"Erreur Win32 YAMDCC : {e}") from e

    def _read_exact(self, handle, size: int, timeout: float) -> bytes:
        chunks: list[bytes] = []
        remaining = size
        deadline = time.time() + timeout

        while remaining > 0:
            if time.time() > deadline:
                raise YAMDCCTimeoutError(f"Timeout lecture pipe après {timeout}s.")

            try:
                _, available, _ = win32pipe.PeekNamedPipe(handle, 0)
            except pywintypes.error:
                available = 0

            if available <= 0:
                time.sleep(0.02)
                continue

            to_read = min(remaining, available)
            _, data = win32file.ReadFile(handle, to_read)

            if not data:
                raise YAMDCCError("Le pipe a été fermé pendant la lecture.")

            chunks.append(data)
            remaining -= len(data)

        return b"".join(chunks)

    def _read_msgpack_object(self, handle, timeout: float) -> Any:
        header = self._read_exact(handle, 4, timeout)
        length = struct.unpack(">i", header)[0]

        if length <= 0:
            return None

        payload = self._read_exact(handle, length, timeout)
        return msgpack.unpackb(payload, raw=False)

    def _write_service_command(self, handle, command: int, int_arg: int) -> None:
        payload = self._pack_service_command_with_int32(command, int_arg)
        frame = struct.pack(">i", len(payload)) + payload

        win32file.WriteFile(handle, frame)

    @staticmethod
    def _pack_service_command_with_int32(command: int, int_arg: int) -> bytes:
        """
        Encode :
            [command, [int_arg]]

        En forçant int_arg en MessagePack int32.

        C'est important parce que le service C# vérifie que l'argument est bien un int.
        """
        if not 0 <= command <= 127:
            raise ValueError("Cette fonction simplifiée attend une commande fixint positive.")

        return (
            bytes(
                [
                    0x92,       # array len 2
                    command,    # positive fixint
                    0x91,       # array len 1
                    0xD2,       # int32
                ]
            )
            + struct.pack(">i", int_arg)
        )

    @staticmethod
    def _parse_response(response: Any) -> tuple[int, list[Any]]:
        if not isinstance(response, list) or len(response) < 2:
            raise YAMDCCError(f"Réponse YAMDCC invalide : {response!r}")

        response_type = response[0]
        response_values = response[1]

        if not isinstance(response_type, int):
            raise YAMDCCError(f"Type de réponse invalide : {response!r}")

        if not isinstance(response_values, list):
            response_values = [response_values]

        return response_type, response_values

    @staticmethod
    def _to_pipe_path(pipe_name: str) -> str:
        if pipe_name.startswith(r"\\.\pipe"):
            return pipe_name

        return rf"\\.\pipe\{pipe_name}"