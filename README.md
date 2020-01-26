# Knucklepucks Fantasy Football Website

## Development

Quick method, Zeit Now development server:

```
now dev
```

Flask server w/ Auto-reload and browser debug mode:

```
python3 -m venv venv
. ./venv/bin/activate
pip install -r requirements.txt
FLASK_APP=index.py FLASK_ENV=development flask run
```

## Deployment

`now`
