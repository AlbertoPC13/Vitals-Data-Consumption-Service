from abc import ABCMeta, abstractmethod
from http import HTTPStatus
from flask import Response


class WearableDeviceDataRetriever(metaclass=ABCMeta):

    @abstractmethod
    def connect_to_api(self) -> str:
        """
        Connect to the API of the wearable device
        :arg: None
        :return: str: Authorization string
        """
        pass

    @abstractmethod
    def get_access_token(self, authorization_code) -> HTTPStatus:
        """
        Get the access token from the API

        :param authorization_code: str: Authorization code
        :return: HTTPStatus: HTTP status code
        """
        pass

    @abstractmethod
    def refresh_access_token(self, refresh_token) -> tuple[str, str]:
        """
        Refresh the access token from the API

        :param refresh_token: str: Refresh token
        :return: tuple: Access token and refresh token
        """
        pass

    @abstractmethod
    def get_user_info(self, user_id) -> str:
        """
        Get user info from the wearable device API

        :param user_id: str: User ID
        :return: str: User info
        """
        pass

    @abstractmethod
    def retrieve_data(self, token, date, scope) -> Response:
        """
        Retrieve data from the wearable device by querying the API

        :param token: str: Authorization token
        :param date: str: Date in 'YYYY-MM-DD' format
        :param scope: List of data scopes to query (e.g., "sleep", "heart_rate").
        :return: JSON response with combined data or error message.
        """
        pass
