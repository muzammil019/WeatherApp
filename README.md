# Real-Time Weather Data Fetching Software

This application fetches and displays real-time weather data for specific locations across seven U.S. states, with a focus on airport weather conditions.

## Features

- Real-time weather data for major U.S. airports and locations
- Modern, responsive web interface
- Automatic data updates
- Detailed weather information including temperature, humidity, wind speed, and more
- Error handling and retry mechanisms
- Easy-to-use location selector

## Setup Instructions

1. Clone this repository
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Get a free API key from [WeatherAPI.com](https://www.weatherapi.com)
4. Create a `.env` file in the project root and add your API key:
   ```
   WEATHER_API_KEY=your_api_key_here
   ```
5. Run the application:
   ```bash
   python app.py
   ```
6. Open your browser and navigate to `http://localhost:5000`

## Supported Locations

- Austin, Texas (Austin-Bergstrom International Airport)
- Chicago, Illinois (O'Hare International Airport)
- Denver, Colorado (Denver International Airport)
- Philadelphia, Pennsylvania (Philadelphia International Airport)
- Miami, Florida (Miami International Airport)
- Los Angeles, California (Los Angeles International Airport)
- New York (Central Park)

## Tech Stack

- Python
- Flask
- WeatherAPI.com
- Bootstrap
- HTML/CSS/JavaScript

## Error Handling

The application includes comprehensive error handling for:
- API request failures
- Invalid locations
- Network issues
- Missing API keys
