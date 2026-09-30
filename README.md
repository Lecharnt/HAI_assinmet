1. Set Up Python
Open a terminal in VS Code using Terminal → New Terminal.
Make sure the terminal is in the project folder, where main.py and requirements.txt are located.
macOS -
  Check that Python is installed:
    python3 --version
  Create a virtual environment:
    python3 -m venv venv
  Activate it:
    source venv/bin/activate
    Your terminal should now show (venv).
Windows -
  Check that Python is installed:
    py --version
  Create a virtual environment:
    py -m venv venv
  Activate it in PowerShell:
    .\venv\Scripts\Activate.ps1
    If PowerShell blocks the activation script, run:
      Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
  Then activate the environment again:
    .\venv\Scripts\Activate.ps1
    Your terminal should now show (venv).
  Note: The virtual environment is created separately on each computer. Do not commit the venv folder to GitHub.



2. Install the Requirements
The project uses a requirements.txt file to list the Python packages it needs.
  With your virtual environment activated, run this command on both macOS and Windows:
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
  This installs the required packages, including:
    Flask: Runs the web application.
    OpenAI: Connects the application to OpenAI models.
    python-dotenv: Loads API keys and configuration from the .env file.
    Requests: Makes HTTP requests to external APIs, including Steam if enabled.
  If the python command is unavailable, use the platform-specific alternative:
    macOS -
      ./venv/bin/python -m pip install -r requirements.txt
    Windows -
      .\venv\Scripts\python.exe -m pip install -r requirements.txt


   
4. Configure API Keys
The project uses API keys to connect to external services. These keys should be stored locally and must not be uploaded to GitHub.
  Create a .env file
  In the main project folder, create a file named:
    .env
  Add your OpenAI API key and Steam API key:
    OPENAI_API_KEY=your_openai_api_key_here
    STEAM_API_KEY=your_steam_api_key_here
    Replace the example values with your own API keys.
Getting an OpenAI API key
  Visit OpenAI API Keys.
  Sign in to your account.
  Create an API key.
  Copy it into your .env file.
Getting a Steam API key:
  Visit Steam Web API Key.
  Sign in to Steam.
  Follow the instructions to register for a key.
  Add the key to your .env file if you use Steam integration.
For Steam game retrieval, the user's Steam Game details privacy setting must allow the library to be accessed.



4. Run the Application
Once the requirements are installed and the .env file is configured, start the Flask application.
  macOS -
    python main.py
    If needed:
      ./venv/bin/python main.py
  Windows -
    py main.py
    If needed:
      .\venv\Scripts\python.exe main.py
If the application starts successfully, the terminal should display a message similar to:
 * Serving Flask app 'main'
 * Debug mode: on
 * Running on http://127.0.0.1:5000

Open the following address in your web browser:
  http://127.0.0.1:5000
