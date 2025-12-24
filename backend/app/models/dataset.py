"""
Dataset models
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, Boolean, BigInteger
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)  # Unique constraint removed - enforced at application level (excluding deleted datasets)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(100), nullable=True)
    
    # Extended fields from coze-loop
    status = Column(String(20), default="Available", index=True)  # Available, Deleted, Expired, Importing, Exporting, Indexing
    item_count = Column(BigInteger, default=0)  # Number of items in dataset
    change_uncommitted = Column(Boolean, default=False)  # Uncommitted changes flag
    latest_version = Column(String(50), nullable=True)  # Latest version number
    next_version_num = Column(BigInteger, default=1)  # Next version number
    biz_category = Column(String(100), nullable=True)  # Business category
    spec = Column(JSON, nullable=True)  # Capacity limits: max_item_count, max_field_count, max_item_size, max_item_data_nested_depth
    features = Column(JSON, nullable=True)  # Features: editSchema, repeatedData, multiModal

    # Relationships
    versions = relationship("DatasetVersion", back_populates="dataset", cascade="all, delete-orphan")


class DatasetVersion(Base):
    __tablename__ = "dataset_versions"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    version = Column(String(50), nullable=False, index=True)
    description = Column(Text, nullable=True)
    schema_id = Column(Integer, ForeignKey("dataset_schemas.id"), nullable=True)  # Made optional for version snapshots
    status = Column(String(20), default="draft")  # draft, active, archived
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(100), nullable=True)
    
    # Extended fields from coze-loop
    version_num = Column(BigInteger, nullable=True)  # Version number
    item_count = Column(BigInteger, default=0)  # Number of items in this version
    evaluation_set_schema = Column(JSON, nullable=True)  # Schema snapshot for this version

    # Relationships
    dataset = relationship("Dataset", back_populates="versions")
    schema = relationship("DatasetSchema", back_populates="versions")
    items = relationship("DatasetItem", back_populates="version", cascade="all, delete-orphan")


class DatasetSchema(Base):
    __tablename__ = "dataset_schemas"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    field_definitions = Column(JSON, nullable=False)  # List of FieldSchema definitions
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    dataset = relationship("Dataset")
    versions = relationship("DatasetVersion", back_populates="schema")


# FieldSchema structure (stored in DatasetSchema.field_definitions as JSON)
# Each field definition contains:
# - key: string (field key)
# - name: string (field name)
# - description: string (optional)
# - content_type: string (Text, Image, Audio, MultiPart)
# - default_display_format: string (PlainText, Markdown, JSON, YAML, Code)
# - status: string (Available, Deleted)
# - text_schema: string (optional, JSON schema for text)
# - multi_model_spec: dict (optional, max_file_count, max_file_size, supported_formats, max_part_count)
# - hidden: bool (whether field is hidden)
# - is_required: bool (whether field is required)
# - default_transformations: list (optional, transformation configs)


class DatasetItem(Base):
    __tablename__ = "dataset_items"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    version_id = Column(Integer, ForeignKey("dataset_versions.id"), nullable=False)
    schema_id = Column(Integer, ForeignKey("dataset_schemas.id"), nullable=True)  # Associated schema
    item_key = Column(String(255), nullable=True, index=True)  # For idempotency
    data_content = Column(JSON, nullable=False)  # Turn structure: {turns: [{id, field_data_list: [{key, name, content}]}]}
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    version = relationship("DatasetVersion", back_populates="items")


class DatasetIOJob(Base):
    __tablename__ = "dataset_io_jobs"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False, index=True)
    job_type = Column(String(50), nullable=False)  # ImportFromFile, ExportToFile, Convert
    status = Column(String(20), default="Pending", index=True)  # Pending, Running, Completed, Failed
    
    # Source and target
    source_file = Column(JSON, nullable=True)  # {provider, path, format, compress_format}
    target_dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=True)
    
    # Field mappings: [{source: str, target: str}]
    field_mappings = Column(JSON, nullable=True)
    
    # Options: {overwrite_dataset: bool}
    option = Column(JSON, nullable=True)
    
    # Progress tracking
    total = Column(BigInteger, nullable=True)  # Total items to process
    processed = Column(BigInteger, default=0)  # Processed items
    added = Column(BigInteger, default=0)  # Successfully added items
    progress = Column(JSON, nullable=True)  # Main progress info
    sub_progresses = Column(JSON, nullable=True)  # Sub-progresses for multiple files
    
    # Error tracking
    errors = Column(JSON, nullable=True)  # List of error groups
    
    # Timestamps
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(100), nullable=True)
    
    # Relationships
    dataset = relationship("Dataset", foreign_keys=[dataset_id])


# Turn structure (stored in DatasetItem.data_content as JSON):
# {
#   "turns": [
#     {
#       "id": int64,
#       "field_data_list": [
#         {
#           "key": string,
#           "name": string,
#           "content": {
#             "content_type": string (Text, Image, Audio, MultiPart),
#             "format": string (PlainText, Markdown, JSON, YAML, Code),
#             "text": string (optional),
#             "image": {
#               "name": string,
#               "url": string,
#               "uri": string,
#               "thumb_url": string,
#               "storage_provider": string
#             } (optional),
#             "multi_part": [Content] (optional),
#             "audio": {
#               "format": string,
#               "url": string
#             } (optional)
#           }
#         }
#       ]
#     }
#   ]
# }

