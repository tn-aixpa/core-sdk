from __future__ import annotations

from digitalhub.entities._base.versioned.builder import VersionedBuilder
from digitalhub.entities._commons.enums import EntityKinds, EntityTypes
from digitalhub.entities.trigger._base.entity import Trigger
from digitalhub.entities.trigger._base.spec import TriggerSpec, TriggerValidator
from digitalhub.entities.trigger._base.status import TriggerStatus


class TriggerTriggerBuilder(VersionedBuilder):
    """
    TriggerTriggerBuilder builder.
    """

    ENTITY_TYPE = EntityTypes.TRIGGER.value
    ENTITY_CLASS = Trigger
    ENTITY_SPEC_CLASS = TriggerSpec
    ENTITY_SPEC_VALIDATOR = TriggerValidator
    ENTITY_STATUS_CLASS = TriggerStatus
    ENTITY_KIND = EntityKinds.TRIGGER_TRIGGER.value

    def build(
        self,
        kind: str,
        project: str,
        name: str,
        uuid: str | None = None,
        description: str | None = None,
        labels: list[str] | None = None,
        **kwargs,
    ) -> Trigger:
        """
        Create a new object.

        Parameters
        ----------
        project : str
            Project name.
        name : str
            Object name.
        kind : str
            Kind the object.
        uuid : str
            ID of the object.
        description : str
            Description of the object (human readable).
        labels : list[str]
            List of labels.
        **kwargs : dict
            Spec keyword arguments.

        Returns
        -------
        Trigger
            Object instance.
        """
        name = self.build_name(name)
        uuid = self.build_uuid(uuid)
        metadata = self.build_metadata(
            project=project,
            name=name,
            description=description,
            labels=labels,
        )
        spec = self.build_spec(
            **kwargs,
        )
        status = self.build_status()
        return self.build_entity(
            project=project,
            name=name,
            uuid=uuid,
            kind=kind,
            metadata=metadata,
            spec=spec,
            status=status,
        )
