from __future__ import annotations

import json
import os
from contextlib import contextmanager

import digitalhub as dh
from kfp import dsl
from kubernetes import client as k8s_client

label_prefix = "kfp-digitalhub-runtime-"


@contextmanager
def pipeline_context():
    try:
        yield PipelineContext()
    finally:
        pass


class PipelineContext:
    def step(
        self,
        name: str,
        function: str | None = None,
        workflow: str | None = None,
        action: str | None = None,
        node_selector: list[dict] | None = None,
        volumes: list[dict] | None = None,
        resources: list[dict] | None = None,
        env: list[dict] | None = None,
        secrets: list[str] | None = None,
        inputs: dict | None = None,
        outputs: dict | None = None,
        parameters: dict | None = None,
        values: list | None = None,
        **kwargs,
    ) -> dsl.ContainerOp:
        """
        Execute a function in DHCore.

        This function creates a KFP ContainerOp that executes a function
        or another workflow in DHCore.
        The function is executed in the context of the current project,
        which is retrieved from DHCore when the pipeline context
        is initialized.

        Parameters
        ----------
        name : str
            The name of the step in KFP.
        function : str
            The name of the function to execute. Either function or workflow must be provided.
        workflow : str
            The Args workflow to execute. Either function or workflow must be provided.
        action : str
            The name of the action to execute. May be omitted in case of workflow execution (defaulting to 'pipeline').
        node_selector : list[dict]
            A list of node selectors for the step.
        volumes : list[dict]
            A list of volumes for the step.
        resources : list[dict]
            A list of resource requirements for the step.
        env : list[dict]
            A list of environment variables for the step.
        secrets : list[str]
            A list of secret names for the step.
        inputs : dict
            A list of complex input parameters.
        outputs : dict
            A list of complex output parameters.
        parameters : dict
            A list of simple input parameters.
        values : list
            A list of simple output parameters.
        kwargs : dict
            Additional keyword arguments to pass to the step.

        Returns
        -------
        dsl.ContainerOp
            A KFP ContainerOp for the step.
        """
        WORKFLOW_IMAGE = os.environ.get("DHCORE_WORKFLOW_IMAGE")
        KFPMETA_DIR = os.environ.get("KFPMETA_OUT_DIR", "/tmp")
        DHCORE_ENDPOINT = os.environ.get("DHCORE_ENDPOINT", "http://localhost:8080/")
        DHCORE_ISSUER = os.environ.get("DHCORE_ISSUER", "http://localhost:8080/")
        PROJECT = os.environ.get("PROJECT_NAME")

        props = {
            "node_selector": node_selector,
            "volumes": volumes,
            "resources": resources,
            "env": env,
            "secrets": secrets,
        }
        props = {k: v for k, v in props.items() if v}

        parameters = {} if parameters is None else parameters
        inputs = {} if inputs is None else inputs
        outputs = {} if outputs is None else outputs
        values = [] if values is None else values

        if function is None and workflow is None:
            raise RuntimeError("Either function or workflow must be provided.")

        if function is not None:
            function_object = dh.get_function(function, project=PROJECT)
            if function_object is None:
                raise RuntimeError(f"Function {function} not found")
        elif workflow is not None:
            workflow_object = dh.get_workflow(workflow, project=PROJECT)
            if workflow_object is None:
                raise RuntimeError(f"Workflow {workflow} not found")
            if action is None:
                action = "pipeline"

        args = {}
        if kwargs is not None:
            args.update(kwargs)

        file_outputs = {
            "mlpipeline-ui-metadata": KFPMETA_DIR + "/mlpipeline-ui-metadata.json",
            "mlpipeline-metrics": KFPMETA_DIR + "/mlpipeline-metrics.json",
            "run_id": "/tmp/run_id",
        }

        cmd = [
            "python",
            "step.py",
            "--project",
            PROJECT,
            "--function" if function is not None else "--workflow",
            function if function is not None else workflow,
            "--function_id" if function is not None else "--workflow_id",
            function_object.id if function is not None else workflow_object.id,
            "--action",
            action,
            "--jsonprops",
            json.dumps(props),
        ]
        # simple input parameters and kwargs
        for param, val in args.items():
            cmd += ["-a", f"{param}={val}"]

        # complex input parameters
        for param, val in inputs.items():
            cmd += ["-ie", f"{param}={val}"]

        # simple input parameters
        for param, val in parameters.items():
            cmd += ["-iv", f"{param}={val}"]

        # complex output parameters
        for param, val in outputs.items():
            cmd += ["-oe", f"{param}={val}"]
            if isinstance(val, dsl.PipelineParam):
                raise Exception("Invalid output specification. cannot use pipeline params")
            else:
                oname = str(val)
            file_outputs[oname.replace(".", "_")] = f"/tmp/entity_{oname}"  # not using path.join to avoid windows "\"

        for param in values:
            cmd += ["-ov", f"{param}"]
            file_outputs[param.replace(".", "_")] = f"/tmp/value_{val}"  # not using path.join to avoid windows "\"

        cop = dsl.ContainerOp(
            name=name,
            image=WORKFLOW_IMAGE,
            command=cmd,
            file_outputs=file_outputs,
        )
        cop.add_pod_label(label_prefix + "project", PROJECT)
        if function is not None:
            cop.add_pod_label(label_prefix + "function", function)
            cop.add_pod_label(label_prefix + "function_id", function_object.id)
        if workflow is not None:
            cop.add_pod_label(label_prefix + "workflow", workflow)
            cop.add_pod_label(label_prefix + "workflow_id", workflow_object.id)
        cop.add_pod_label(label_prefix + "action", action)

        cop.container.add_env_variable(k8s_client.V1EnvVar(name="DHCORE_ENDPOINT", value=DHCORE_ENDPOINT))
        cop.container.add_env_variable(k8s_client.V1EnvVar(name="DHCORE_ISSUER", value=DHCORE_ISSUER))

        # RUN_SECRET_NAME = "digitalhub-common-creds"
        RUN_SECRET_NAME = os.environ.get("DH_RUN_SECRET_NAME")

        if RUN_SECRET_NAME is not None:
            # user credentials from secret in steps
            names = [
                "DHCORE_ACCESS_TOKEN",
                "DHCORE_REFRESH_TOKEN",
                "DHCORE_CLIENT_ID",
                "DHCORE_AUTH_SUB",
                "DHCORE_USER",
                "DHCORE_PASSWORD",
            ]
            for name in names:
                cop.container.add_env_variable(
                    k8s_client.V1EnvVar(
                        name=name,
                        value_from=k8s_client.V1EnvVarSource(
                            secret_key_ref=k8s_client.V1SecretKeySelector(name=RUN_SECRET_NAME, key=name, optional=True)
                        ),
                    )
                )
        return cop
