"""Start the website:  python start_app.py   (or press F5 in VS Code)."""
import os

from webapp import create_app

app = create_app()

if __name__ == "__main__":
   
    app.run(debug=True, port=int(os.environ.get("PORT", 5002)))
