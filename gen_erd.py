import db
import eralchemy

eralchemy.render_er(db.Base, "erd.png")
