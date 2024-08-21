import os

from dotenv import load_dotenv

load_dotenv()


class ConfigurationError(Exception): ...


def load_credentials() -> list[tuple[str]]:
    """
    It's possible to use up to 9 users (for now)
    You have to store your creds like
    ```bash
    CREDENTIALS_1="dummy1@email.com:password"
    CREDENTIALS_2="dummy2@email.com:password"
    ...
    CREDENTIALS_9="dummy9@email.com:password"
    ```
    """

    def split_by_colon(value: str) -> tuple[str, str]:
        pos = value.find(":")
        if pos == -1:
            raise ConfigurationError(
                "Incorrect configuration provided. Expected email:password pair"
            )
        return value[:pos], value[pos + 1 :]

    raw_creds = [os.getenv(f"CREDENTIALS_{i}") for i in range(1, 10)]
    raw_creds = [creds for creds in raw_creds if creds]

    return [split_by_colon(cred) for cred in raw_creds]
