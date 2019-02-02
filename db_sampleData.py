from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import Electronic, Base, Item, User

engine = create_engine('sqlite:///catalog_db.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()


# Delete Categories if exisitng.
session.query(Electronic).delete()
# Delete Items if exisitng.
session.query(Item).delete()
# Delete Users if exisitng.
session.query(User).delete()

# Create dummy user
user1 = User(name="Norah Ali", email="nora@example.com",
             picture='https://cdn3.iconfinder.com/data/icons/black-easy/512/538642-user_512x512.png')
session.add(user1)
session.commit()

# Menu for UrbanBurger
electronic1 = Electronic( name="Laptops",user=user1)

session.add(electronic1)
session.commit()

item1 = Item( name="Dell Inspiron 15", description="5.6 inch Full HD Touchscreen Backlit Keyboard Laptop PC, Intel Core i5-8250U Quad-Core, 8GB DDR4, 1TB HDD, Bluetooth 4.2, WIFI, Windows 10",
                     price="$543.24", electronic=electronic1,user=user1)

session.add(item1)
session.commit()


item2 = Item(name="Apple MacBook Pro ", description="13 Retina, Touch Bar, 2.3GHz Quad-Core Intel Core i5, 8GB RAM, 256GB SSD - Space Gray ",
                     price="$1,706.68", electronic=electronic1,user=user1)

session.add(item2)
session.commit()

item3 = Item( name="HP", description="15.6\" Touch Screen Laptop with Intel Core i3 Processor, 8GB RAM, 1TB Hard Drive, HDMI, USB 3.1, Bluetooth, Windows 10 - Jet black",
                     price="$418.88", electronic=electronic1,user=user1)

session.add(item3)
session.commit()

electronic1 = Electronic( name="TV's",user=user1)

session.add(electronic1)
session.commit()

item1 = Item( name="Toshiba", description="32-inch 720p HD Smart LED TV - Fire TV Edition",
	                 price="$180.00", electronic=electronic1,user=user1)

session.add(item1)
session.commit()


item2 = Item( name="Insignia ", description="24-inch 720p HD Smart LED TV- Fire TV Edition",
                     price="$150.12", electronic=electronic1,user=user1)

session.add(item2)
session.commit()

item3 = Item( name="TCL ", description="32-Inch 720p Roku Smart LED TV (2017 Model)",
                     price="$199.99", electronic=electronic1,user=user1)

session.add(item3)
session.commit()

electronic1 = Electronic( name="Tablets",user=user1)

session.add(electronic1)
session.commit()

item1 = Item( name="Apple iPad Pro", description="11-inch, Wi-Fi, 256GB - Space Gray (Latest Model)",
	                 price="$950.00", electronic=electronic1,user=user1)

session.add(item1)
session.commit()


item2 = Item(name="Samsung Galaxy Tab S3", description="9.7-Inch, 32GB Tablet - Silver",
                     price="$550.12", electronic=electronic1,user=user1)

session.add(item2)
session.commit()

item3 = Item( name="Microsoft Surface Go", description="(Intel Pentium Gold, 4GB RAM, 64GB)",
                     price="$394.99", electronic=electronic1,user=user1)

session.add(item3)
session.commit()

print "added Fake menu items!"