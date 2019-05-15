from contextlib import contextmanager

@contextmanager
def session_scope(sessionmaker):
    session = sessionmaker()
    try:
        yield session
        # session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()
