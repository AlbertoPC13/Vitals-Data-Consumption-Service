from flask import session

from vitals_data_retrieving.data_consumption_tools.wearable_devices_retrieving.WearableDeviceDataRetriever import \
    WearableDeviceDataRetriever


class VitalsDataRetrievingService:
    def __init__(self, device_data_retriever: WearableDeviceDataRetriever):
        """
        Initialize the service with the device data retriever
        :param device_data_retriever: WearableDeviceDataRetriever: The device data retriever passed by dependency injection
        """
        self.device_data_retriever = device_data_retriever

    def get_access_to_api(self) -> str:
        """
        Get access to the API of the wearable device
        :return: str: Authorization URL
        """
        return self.device_data_retriever.connect_to_api()

    def get_user_info_from_api(self, token) -> str:
        """
        Get user info from the wearable device API
        :return: str: User info
        """
        return self.device_data_retriever.get_user_info(token)

    def get_data_from_wearable_device_api(
            self, token: str = None, start_date: str = None, end_date: str = None, scope: list[str] = None) -> str:
        """
        Get data from the wearable device API
        :return: str: Data
        """
        return self.device_data_retriever.retrieve_data(token, start_date, end_date, scope)

    def callback_action(self, authorization_response) -> str:
        """
        Handle the callback from the wearable device API
        :param authorization_response: str: URL
        :return: str: User ID
        """
        authorization_token = self.device_data_retriever.get_authorization_token(authorization_response)
        session['oauth_token'] = authorization_token
        user_id = session.get('oauth_token').get('user_id', None)
        return authorization_token
