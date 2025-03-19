<div align="center">

  # TeleGemini NT
  
  **A Python Telegram bot powered by Google's `gemini` LLM API**

  *This is a Python Telegram bot that uses Google's gemini LLM API to generate creative text formats based on user input. It is designed to be a fun and interactive way to explore the possibilities of large language models.*

*This is the upgrade of original "gemini-pro" and support more feature.*
</div>

### Features

* Generate creative text formats like poems, code, scripts, musical pieces, etc.
* Stream the generation process, so you can see the text unfold in real-time.
* Reply to your messages with Bard's creative output.
* Easy to use with simple commands:
    * `/start`: Greet the bot and get started.
    * `/help`: Get information about the bot's capabilities.
    * `/admin`: Add/Delete/Check bot admin command.
    * `/instruction`: Set/Restore system instruction.
* Send any text message to trigger the generation process.
* Send any image with captions to generate responses based on the image. (Multi-modal support)
* User authentication to prevent unauthorized access by setting `AUTHORIZED_USERS` in the `.env` file (optional).

### Requirements

* Python 3.10+
* Telegram Bot API token
* Google `gemini` API key
* dotenv (for environment variables)


### Installation

1. Clone this repository.
2. Install the required dependencies:
    * `pipenv install` (if using pipenv)
    * `pip install -r requirements.txt` (if not using pipenv)
3. Create a `.env` file and add the following environment variables:
    * `BOT_TOKEN`: Your Telegram Bot API token. You can get one by talking to [@BotFather](https://t.me/BotFather).
    * `GOOGLE_API_KEY`: Your Google Bard API key. You can get one from [Google AI Studio](https://makersuite.google.com/).
    * `AUTHORIZED_USERS`: A comma-separated list of Telegram usernames or user IDs that are authorized to access the bot. (optional) Example value: `shonan23,1234567890`
    * `ADMINS`: Set who control the bot. The first one is owner and only he/she can add/delete other admin Example value: `ADMINS='1262948436,xxxxxx,xxxxx` make sure that is your telegram ID
    * INSTRUCTION : Set what you want your bot remind.
    * INSTRUCTION_ORIGINAL : Set the default instruction in order to prevent some admin change to another instruction and you lost the one you need.
4. Run the bot:
    * `python main.py` (if not using pipenv)
    * `pipenv run python main.py` (if using pipenv)

### Usage

1. Start the bot by running the script.
   ```shell
   python main.py
   ```
2. Open the bot in your Telegram chat.
3. Send any text message to the bot.
4. The bot will generate creative text formats based on your input and stream the results back to you.
5. If you want to restrict public access to the bot, you can set `AUTHORIZED_USERS` in the `.env` file to a comma-separated list of Telegram user IDs. Only these users will be able to access the bot.
    Example:
    ```shell
    AUTHORIZED_USERS=shonan23,1234567890
    ```



### Star History

<a href="https://www.star-history.com/#u0-ani-nya/TeleGemini_NT&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=u0-ani-nya/TeleGemini_NT&type=Date&theme=dark" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=u0-ani-nya/TeleGemini_NT&type=Date" />
    <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=u0-ani-nya/TeleGemini_NT&type=Date" />
  </picture>
</a>

### Contributing

We welcome contributions to this project. Please feel free to fork the repository and submit pull requests.

### Disclaimer

This bot is still under development and may sometimes provide nonsensical or inappropriate responses. Use it responsibly and have fun!

### License

This is a free and open-source project released under the GNU Affero General Public License v3.0 license. See the LICENSE file for details.
