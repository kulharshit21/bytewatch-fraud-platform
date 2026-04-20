from __future__ import annotations

import uvicorn
from fastapi import FastAPI, HTTPException

from fraud_platform_common.config import RuntimeSettings
from fraud_platform_common.service import create_service_app, dependency_from_url
from fraud_platform_trainer.training import FraudTrainer


class TrainerSettings(RuntimeSettings):
    service_name: str = "trainer"
    host: str = "0.0.0.0"

    def __init__(self, **values: object) -> None:
        super().__init__(**values)
        self.port = self.trainer_port


def _build_trainer(app: FastAPI) -> None:
    app.state.trainer = FraudTrainer(app.state.settings)


def build_app() -> FastAPI:
    settings = TrainerSettings()
    app = create_service_app(
        settings=settings,
        description="Model training, MLflow registration, and Evidently drift reporting service.",
        dependencies=[
            dependency_from_url("postgres", settings.database_url, 5432),
            dependency_from_url("mlflow", settings.mlflow_tracking_uri, 5000),
        ],
        extra_metadata={
            "role": "trainer and retraining orchestrator",
            "model_name": settings.mlflow_model_name,
        },
        startup_callbacks=[_build_trainer],
    )
    trainer_routes(app)
    return app


def trainer_routes(app: FastAPI) -> None:
    @app.get("/training/status", tags=["training"])
    async def training_status() -> dict[str, object]:
        trainer: FraudTrainer = app.state.trainer
        metadata = trainer.get_current_metadata()
        return {
            "current_model": None if metadata is None else metadata.model_dump(mode="json"),
            "tracking_uri": app.state.settings.mlflow_tracking_uri,
        }

    @app.post("/training/bootstrap", tags=["training"])
    async def training_bootstrap(force: bool = False) -> dict[str, object]:
        trainer: FraudTrainer = app.state.trainer
        result = trainer.bootstrap_model(force=force)
        return {
            "dataset_path": result.dataset_path,
            "metadata": result.metadata.model_dump(mode="json"),
            "metrics": result.metrics,
            "thresholds": result.thresholds,
            "drift_report_html": result.drift_report_html,
            "drift_report_json": result.drift_report_json,
        }

    @app.post("/training/run", tags=["training"])
    async def training_run(source: str = "database", alias: str | None = None) -> dict[str, object]:
        trainer: FraudTrainer = app.state.trainer
        if source == "database":
            result = trainer.train_from_repository(alias=alias)
        elif source == "csv":
            result = trainer.train_from_csv(app.state.settings.producer_export_path, alias or app.state.settings.mlflow_champion_alias)
        else:
            raise HTTPException(status_code=400, detail="source must be 'database' or 'csv'")
        return {
            "dataset_path": result.dataset_path,
            "metadata": result.metadata.model_dump(mode="json"),
            "metrics": result.metrics,
            "thresholds": result.thresholds,
        }

    @app.post("/training/drift", tags=["training"])
    async def training_drift(sample_size: int = 500) -> dict[str, object]:
        trainer: FraudTrainer = app.state.trainer
        return trainer.generate_drift_report(sample_size=sample_size)


app = build_app()


def run() -> None:
    settings = TrainerSettings()
    uvicorn.run("fraud_platform_trainer.main:app", host=settings.host, port=settings.port, reload=False)
