from fastapi import APIRouter
import run_model  # will not trigger Typer CLI

router = APIRouter()

@router.post("/predict")
def predict_endpoint(payload: dict):
    # Call the main logic directly
    # Here you must pass parameters in the way main() expects
    result = run_model.main(
        payload["config_file"]
    )
    return {"result": result}
