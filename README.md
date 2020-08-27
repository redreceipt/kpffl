# Knucklepucks Fantasy Football Website

## Development

Quick method, Vercel development server:

```
vercel dev
```

Flask server w/ Auto-reload and browser debug mode:

```
python3 -m venv venv
. ./venv/bin/activate
pip install -r requirements.txt
FLASK_APP=index.py FLASK_ENV=development flask run
```

## Preview Deployment

`vercel`

or push a branch to github, preview site will be located at `kpffl-git-<branch>.<github-user>.vercel.app`

## Production Deployment

`vercel --prod`

or push to `master` on Github

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
- [MongoDB](https://www.mongodb.com/)
- [FontAwesome](https://fontawesome.com/)
- [Bootstrap](https://getbootstrap.com/)
