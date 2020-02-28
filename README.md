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

## Manage Database

Connect to the database:

`mongo "<MONGO_URI>"`

List the collections:

`db.getCollectionNames()`

Show all items:

`db.collection.find()`

Find an item:

`db.collection.find( {_id: <ID>} )`

## Credits

### Tech Stack

- [Flask](https://palletsprojects.com/p/flask/)
- [Zeit Now](https://zeit.co/)
- [Auth0](https://auth0.com/)
- [MongoDB](https://www.mongodb.com/)
- [FontAwesome](https://fontawesome.com/)
- [Bootstrap 3](https://getbootstrap.com/docs/3.3/)
