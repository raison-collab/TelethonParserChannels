from sqlalchemy import Column, Integer, String, ForeignKey, Table, Boolean, DateTime
from sqlalchemy.orm import relationship, DeclarativeBase


class Base(DeclarativeBase):
    pass


# class AllChatModel(Base):
#     __tablename__ = 'all_chats'
#     id = Column(Integer, primary_key=True, autoincrement=True)
#     chat_id = Column(String(length=250), nullable=False, unique=True, index=True)
#     chat_name = Column(String, nullable=False)


class ListeningChatModel(Base):
    __tablename__ = 'listening_chats'
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(String, unique=True, nullable=False, index=True)


theme_keyword_association = Table(
    'theme_keyword_association',
    Base.metadata,
    Column('theme_id', ForeignKey('themes.id'), primary_key=True),
    Column('keyword_id', ForeignKey('keywords.id'), primary_key=True)
)


class ThemeModel(Base):
    __tablename__ = 'themes'
    id = Column(Integer, primary_key=True, autoincrement=True)
    theme_name = Column(String, unique=True, nullable=False, index=True)
    is_following = Column(Boolean, nullable=False, default=False)
    keywords = relationship("KeywordsModel", secondary=theme_keyword_association, back_populates="themes")


class KeywordsModel(Base):
    __tablename__ = 'keywords'
    id = Column(Integer, primary_key=True, autoincrement=True)
    word = Column(String, unique=True, nullable=False, index=True)
    themes = relationship("ThemeModel", secondary=theme_keyword_association, back_populates="keywords")


class MessagesModel(Base):
    __tablename__ = 'messages'
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(String, nullable=False, index=True)
    message_id = Column(String, nullable=False, index=True)
    message = Column(String, nullable=False)
    grouped_id = Column(Integer, default=None,  nullable=True, index=True)
    date = Column(DateTime, nullable=False)
    links = Column(String, nullable=True, default=None)

    files = relationship("FilesModel", back_populates="message")


class FilesModel(Base):
    __tablename__ = 'files'
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String, unique=True, nullable=False, index=True)
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_type = Column(String, nullable=False, index=True)
    message_id = Column(String, ForeignKey('messages.id'), index=True, nullable=False)
    chat_id = Column(String, ForeignKey('listening_chats.id'), index=True, nullable=False)
    original_filename = Column(String, nullable=True, default=None)

    # Связь с MessagesModel
    message = relationship("MessagesModel", back_populates="files")
