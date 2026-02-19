#!/usr/bin/env python3

from rss import app

if __name__ == "__main__":
    # Dev uniquement — en prod, gunicorn charge rss:app directement
    app.run(debug=True, host="0.0.0.0", port=14000)
