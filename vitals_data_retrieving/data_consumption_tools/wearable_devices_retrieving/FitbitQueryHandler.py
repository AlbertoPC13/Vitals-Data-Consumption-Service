from __future__ import annotations

from http import HTTPStatus
from typing import Tuple
from flask import session, jsonify, Response
import requests


class FitbitQueryHandler:
    def __init__(self, token: str):
        try:
            self.headers = {'Authorization': f'Bearer {token}',
                            'Accept-Language': 'en_US'}
        except KeyError:
            raise KeyError('No access token found in session')

    def get_user_info(self, date: str = None) -> tuple[str, HTTPStatus] | Response:
        """
        Get user info from the wearable device API

        :arg: None
        :return: user info
        """
        try:
            # Endpoint for User Info data
            endpoint = f"https://api.fitbit.com/1/user/-/devices.json"
            response = requests.get(endpoint, headers=self.headers)
            formatted_response = response.json()

            return formatted_response, HTTPStatus.OK

        except Exception as e:
            return jsonify({'error': f"An error occurred during data fetch: {str(e)}"})

    def get_sleep_data(self, date: str = None) -> tuple[str, HTTPStatus] | Response:
        """
        Get user's sleep log entries for a given date. The detail level: duration (minutes), efficiency, minutes of
        the sleep stages (deep, light, rem, wake)

        :param date: Date in 'YYYY-MM-DD' format.
        :return: sleep data
        """
        try:
            # Endpoint for Sleep Log by Date data
            endpoint = f"https://api.fitbit.com/1.2/user/-/sleep/date/{date}.json"
            response = requests.get(endpoint, headers=self.headers)
            formatted_response = response.json()
            
            # Process the sleep data
            sleep_data = formatted_response.get('sleep', [])
            primary_sleep = sleep_data[0]  
            duration_ms = primary_sleep.get('duration', 0)
            duration_minutes = round(duration_ms / (1000 * 60), 2)  # Convert to minutes
            
            result = {
                'query_date': date,
                'duration_minutes': duration_minutes,
                'efficiency': primary_sleep.get('efficiency', None),
                'stages': primary_sleep.get('levels', {}).get('summary', {}),
            }

            return result, HTTPStatus.OK

        except Exception as e:
            return jsonify({'error': f"An error occurred during data fetch: {str(e)}"})

    def get_heart_rate_data(self, date: str = None) -> tuple[str, HTTPStatus] | Response:
        """
        Get heart rate data for a specific second from the wearable device API.

        :param date: Date in 'YYYY-MM-DD' format.
        :return: Heart rate data for the specified second.
        """
        try:
            # Endpoint for Heart Rate Intraday by Date data
            endpoint = f"https://api.fitbit.com/1/user/-/activities/heart/date/{date}/1d/1sec.json"
            response = requests.get(endpoint, headers=self.headers)
            formatted_response = response.json()
            
            heart_data = formatted_response.get('activities-heart-intraday', {}).get('dataset', [])
            heart_rates = [entry['value'] for entry in heart_data]
            
            # Process the heart rate data
            processed_data = [
                {"time": entry["time"], "heart_rate": entry["value"]}
                for entry in heart_data
            ]
            
            # Calculate the RHR as the average of the lowest 10% heart rates
            sorted_heart_rates = sorted(heart_rates)
            threshold_index = max(1, len(sorted_heart_rates) // 10)  # At least 1 value
            resting_heart_rate_values = sorted_heart_rates[:threshold_index]
            rhr = round(sum(resting_heart_rate_values) / len(resting_heart_rate_values), 2)
            
            result = {
                "query_date": date,
                "heart_rate_data": processed_data
                
            }
            
            resultRHR = {
                "query_date": date,
                "resting_heart_rate": rhr,
                "resting_heart_rate_values": resting_heart_rate_values
            }

            return result, resultRHR, HTTPStatus.OK

        except Exception as e:
            return jsonify({'error': f"An error occurred during data fetch: {str(e)}"})

    def get_heart_rate_variability_data(self, date: str = None) -> tuple[str, HTTPStatus] | Response:
        """
        Get heart rate variability data for a specific second from the wearable device API.

        :param date: Date in 'YYYY-MM-DD' format.
        :return: Heart rate data for the specified second.
        """
        try:
            # Endpoint for Heart Rate Variability Intraday by Date data
            endpoint = f"https://api.fitbit.com/1/user/-/hrv/date/{date}/all.json"
            response = requests.get(endpoint, headers=self.headers)
            formatted_response = response.json()
            
            rr_intervals = formatted_response.get('rr_intervals', [])
            
             # Calculate RMSSD
            rr_differences = np.diff(rr_intervals)  # Differences between successive RR intervals
            squared_differences = np.square(rr_differences)
            rmssd = np.sqrt(np.mean(squared_differences))
            
            # Calculate coverage
            total_intervals = len(rr_intervals)
            expected_intervals = 1440  # Assumes 24 hours of 1-minute intervals
            coverage = round((total_intervals / expected_intervals) * 100, 2)
            
            # Frequency-domain analysis using Welch's method
            fs = 1 / (np.mean(rr_intervals) / 1000)  # Sampling frequency in Hz (mean RR in ms converted to seconds)
            f, power = welch(rr_intervals, fs=fs, nperseg=min(256, total_intervals))
            
            # Calculate LF and HF power
            lf_band = (0.04, 0.15)
            hf_band = (0.15, 0.4)
            lf_power = np.trapz(power[(f >= lf_band[0]) & (f <= lf_band[1])], f[(f >= lf_band[0]) & (f <= lf_band[1])])
            hf_power = np.trapz(power[(f >= hf_band[0]) & (f <= hf_band[1])], f[(f >= hf_band[0]) & (f <= hf_band[1])])
            
            result = {
                "query_date": date,
                "rmssd": round(rmssd, 2),
                "coverage_percentage": coverage,
                "lf_power": round(lf_power, 2),
                "hf_power": round(hf_power, 2)
            }
            
            return formatted_response, HTTPStatus.OK

        except Exception as e:
            return jsonify({'error': f"An error occurred during data fetch: {str(e)}"})
        
    def get_breathing_rate_data(self, date: str = None) -> tuple[str, HTTPStatus] | Response:
        """
        Get respiratory rate intraday data for a specific date.
        Calculates average respiratory rate and classifies rates by sleep stages.

        :param date: Date for the data (format YYYY-MM-DD).
        :return: Respiratory rate data and classification by sleep stages.
        """
        try:
            # Endpoint for Breathing Rate Intraday by Date data
            endpoint = f"https://api.fitbit.com/1/user/-/br/date/{date}/all.json"
            response = requests.get(endpoint, headers=self.headers)
            formatted_response = response.json()
            
            sleep_data = formatted_response['sleep']
            
            # Initialize accumulators for calculations
            total_breaths = 0
            total_minutes = 0
            stage_breaths = {'deep': 0, 'light': 0, 'rem': 0, 'wake': 0}
            stage_minutes = {'deep': 0, 'light': 0, 'rem': 0, 'wake': 0}
            
            # Process the sleep records
            for record in sleep_data:
                if 'levels' in record and 'data' in record['levels']:
                    for stage in record['levels']['data']:
                        stage_name = stage['level']
                        minutes = stage['seconds'] / 60
                        breaths = stage.get('breaths', 0)  # Replace with actual key if different
                        total_breaths += breaths
                        total_minutes += minutes
                        
                        if stage_name in stage_breaths:
                            stage_breaths[stage_name] += breaths
                            stage_minutes[stage_name] += minutes
                            
            # Calculate averages
            overall_avg_breaths = round(total_breaths / total_minutes, 2) if total_minutes > 0 else 0
            stage_avg_breaths = {
                level: round(stage_breaths[level] / stage_minutes[level], 2) if stage_minutes[level] > 0 else 0
                for level in stage_breaths
            }
            
            result = {
                "query_date": date,
                "overall_avg_breaths_per_minute": overall_avg_breaths,
                "stage_avg_breaths_per_minute": stage_avg_breaths
            }
                        
            return result, HTTPStatus.OK

        except Exception as e:
            return jsonify({'error': f"An error occurred during data fetch: {str(e)}"})
    
    def get_oxygen_saturation_data(self, date: str = None) -> tuple[str, HTTPStatus] | Response:
        """
        Get intraday SpO2 (oxygen saturation) data for a specific date.
        Calculates average SpO2 and provides detailed data at 1-second intervals.

        :param date: Date for the data (format YYYY-MM-DD).
        :return: SpO2 data with average and detailed measurements.
        """
        try:
            
            # Endpoint for SpO2 Intraday by Date data
            endpoint = f"https://api.fitbit.com/1/user/-/spo2/date/{date}/all.json"
            response = requests.get(endpoint, headers=self.headers)
            formatted_response = response.json()
            

            return formatted_response, HTTPStatus.OK

        except Exception as e:
            return jsonify({'error': f"An error occurred during data fetch: {str(e)}"})
        
    def get_activity_data(self, date: str = None) -> tuple[str, HTTPStatus] | Response:
        """
        GGet intraday activity time series data (steps) for a specific date.
        Provides detailed step counts at 1-minute intervals.
        :param date: Date for the data (format YYYY-MM-DD).
        :return: Step count data with detailed measurements at 1-minute intervals.
        
        """
        try:
            # Endpoint for activity steps data
            endpoint = f"https://api.fitbit.com/1/user/-/activities/steps/date/{date}/1d/1min.json"
            response = requests.get(endpoint, headers=self.headers)
            formatted_response = response.json()
            
            return formatted_response, HTTPStatus.OK

        except Exception as e:
            return jsonify({'error': f"An error occurred during data fetch: {str(e)}"})
