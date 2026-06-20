import freqtrade.persistence.models as models
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import scoped_session, sessionmaker

_original_init_db = models.init_db


def patched_init_db(db_url: str) -> None:
    from freqtrade.persistence.models import (
        ModelBase, Trade, Order, PairLock,
        _KeyValueStoreModel, _CustomData, WalletHistory,
        check_migrate, get_request_or_thread_id,
    )
    from sqlalchemy.pool import StaticPool
    from sqlalchemy.exc import NoSuchModuleError
    from freqtrade.exceptions import OperationalException

    kwargs = {}

    if db_url.startswith("postgresql"):
        kwargs.update({
            "pool_size": 2,
            "max_overflow": 3,
            "pool_pre_ping": True,
            "pool_recycle": 300,
        })

    if db_url == "sqlite://":
        kwargs["poolclass"] = StaticPool

    if db_url.startswith("sqlite://"):
        kwargs["connect_args"] = {"check_same_thread": False}

    try:
        engine = create_engine(db_url, future=True, **kwargs)
    except Exception as e:
        raise OperationalException(f"Database connection failed: {e}")

    Trade.session = scoped_session(
        sessionmaker(bind=engine, autoflush=False), scopefunc=get_request_or_thread_id
    )
    Order.session = Trade.session
    PairLock.session = Trade.session
    _KeyValueStoreModel.session = Trade.session
    _CustomData.session = scoped_session(
        sessionmaker(bind=engine, autoflush=True), scopefunc=get_request_or_thread_id
    )
    WalletHistory.session = Trade.session

    previous_tables = inspect(engine).get_table_names()
    ModelBase.metadata.create_all(engine)
    check_migrate(engine, decl_base=ModelBase, previous_tables=previous_tables)

    print(f"DB pool: size=2, max_overflow=3, pre_ping=True")


models.init_db = patched_init_db
print("DB pool patch applied")
