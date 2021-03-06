# Copyright Contributors to the Amundsen project.
# SPDX-License-Identifier: Apache-2.0

from typing import (
    Iterator, List, Tuple, Union,
)

from amundsen_common.utils.atlas import AtlasCommonParams, AtlasTableTypes
from amundsen_rds.models import RDSModel
from amundsen_rds.models.table import TableWatermark as RDSTableWatermark

from databuilder.models.atlas_entity import AtlasEntity
from databuilder.models.atlas_relationship import AtlasRelationship
from databuilder.models.atlas_serializable import AtlasSerializable
from databuilder.models.graph_node import GraphNode
from databuilder.models.graph_relationship import GraphRelationship
from databuilder.models.graph_serializable import GraphSerializable
from databuilder.models.table_serializable import TableSerializable
from databuilder.serializers.atlas_serializer import (
    add_entity_relationship, get_entity_attrs, get_entity_relationships,
)
from databuilder.utils.atlas import AtlasSerializedEntityOperation


class Watermark(GraphSerializable, TableSerializable, AtlasSerializable):
    """
    Table watermark result model.
    Each instance represents one row of table watermark result.
    """
    LABEL = 'Watermark'
    KEY_FORMAT = '{database}://{cluster}.{schema}' \
                 '/{table}/{part_type}/'
    WATERMARK_TABLE_RELATION_TYPE = 'BELONG_TO_TABLE'
    TABLE_WATERMARK_RELATION_TYPE = 'WATERMARK'

    def __init__(self,
                 create_time: str,
                 database: str,
                 schema: str,
                 table_name: str,
                 part_name: str,
                 part_type: str = 'high_watermark',
                 cluster: str = 'gold',
                 ) -> None:
        self.create_time = create_time
        self.database = database
        self.schema = schema
        self.table = table_name
        self.parts: List[Tuple[str, str]] = []

        if '=' not in part_name:
            raise Exception('Only partition table has high watermark')

        # currently we don't consider nested partitions
        idx = part_name.find('=')
        name, value = part_name[:idx], part_name[idx + 1:]
        self.parts = [(name, value)]
        self.part_type = part_type
        self.cluster = cluster
        self._node_iter = self._create_node_iterator()
        self._relation_iter = self._create_relation_iterator()
        self._record_iter = self._create_next_record()
        self._atlas_entity_iterator = self._create_next_atlas_entity()

    def __repr__(self) -> str:
        return f"Watermark(create_time={str(self.create_time)!r}, database={self.database!r}, " \
               f"schema={self.schema!r}, table={self.table!r}, parts={self.parts!r}, " \
               f"cluster={self.cluster!r}, part_type={self.part_type!r})"

    def create_next_node(self) -> Union[GraphNode, None]:
        # return the string representation of the data
        try:
            return next(self._node_iter)
        except StopIteration:
            return None

    def create_next_relation(self) -> Union[GraphRelationship, None]:
        try:
            return next(self._relation_iter)
        except StopIteration:
            return None

    def create_next_record(self) -> Union[RDSModel, None]:
        try:
            return next(self._record_iter)
        except StopIteration:
            return None

    def get_watermark_model_key(self) -> str:
        return Watermark.KEY_FORMAT.format(database=self.database,
                                           cluster=self.cluster,
                                           schema=self.schema,
                                           table=self.table,
                                           part_type=self.part_type)

    def get_metadata_model_key(self) -> str:
        return f'{self.database}://{self.cluster}.{self.schema}/{self.table}'

    def _create_node_iterator(self) -> Iterator[GraphNode]:
        """
        Create watermark nodes
        :return:
        """
        for part in self.parts:
            part_node = GraphNode(
                key=self.get_watermark_model_key(),
                label=Watermark.LABEL,
                attributes={
                    'partition_key': part[0],
                    'partition_value': part[1],
                    'create_time': self.create_time
                }
            )
            yield part_node

    def _create_relation_iterator(self) -> Iterator[GraphRelationship]:
        """
        Create relation map between watermark record with original table
        :return:
        """
        relation = GraphRelationship(
            start_key=self.get_watermark_model_key(),
            start_label=Watermark.LABEL,
            end_key=self.get_metadata_model_key(),
            end_label='Table',
            type=Watermark.WATERMARK_TABLE_RELATION_TYPE,
            reverse_type=Watermark.TABLE_WATERMARK_RELATION_TYPE,
            attributes={}
        )
        yield relation

    def _create_next_record(self) -> Iterator[RDSModel]:
        """
        Create watermark records
        """
        for part in self.parts:
            part_record = RDSTableWatermark(
                rk=self.get_watermark_model_key(),
                partition_key=part[0],
                partition_value=part[1],
                create_time=self.create_time,
                table_rk=self.get_metadata_model_key()
            )
            yield part_record

    def _create_atlas_partition_entity(self, spec: Tuple[str, str]) -> AtlasEntity:
        attrs_mapping = [
            (AtlasCommonParams.qualified_name, self.get_watermark_model_key()),
            ('name', spec[1]),
            ('displayName', spec[1]),
            ('key', spec[0]),
            ('create_time', self.create_time)
        ]

        entity_attrs = get_entity_attrs(attrs_mapping)

        relationship_list = []  # type: ignore

        add_entity_relationship(
            relationship_list,
            'table',
            AtlasTableTypes.table,
            self.get_metadata_model_key()
        )

        entity = AtlasEntity(
            typeName=AtlasTableTypes.watermark,
            operation=AtlasSerializedEntityOperation.CREATE,
            attributes=entity_attrs,
            relationships=get_entity_relationships(relationship_list)
        )

        return entity

    def create_next_atlas_relation(self) -> Union[AtlasRelationship, None]:
        pass

    def _create_next_atlas_entity(self) -> Iterator[AtlasEntity]:
        for part in self.parts:
            yield self._create_atlas_partition_entity(part)

    def create_next_atlas_entity(self) -> Union[AtlasEntity, None]:
        try:
            return next(self._atlas_entity_iterator)
        except StopIteration:
            return None
