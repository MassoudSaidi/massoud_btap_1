from fastapi import APIRouter, Form
from fastapi import FastAPI, UploadFile, File
from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from io import BytesIO
from datetime import datetime

import json
import pandas as pd
from typing import List, Dict, Optional
from ..api_config import settings

from run_model import run_predictions  # will not trigger Typer CLI
import boto3
from botocore.exceptions import BotoCoreError, ClientError

router = APIRouter()

s3 = boto3.client("s3")
BUCKET_NAME = settings.BUCKET_NAME

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    email: Optional[str] = Form(None, description="Optional user email address")
):
    try:

        # Validate file extension
        if not file.filename.lower().endswith('.xlsx'):
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Only .xlsx files are permitted for upload. Please ensure your file is in the correct format and try again."
            )
                
        if email:
            # Sanitize email: lowercase, replace non-alphanumeric with '_', remove leading/trailing '_'
            sanitized_email = ''.join(c if c.isalnum() else '_' for c in email.lower()).strip('_')
            prefix = sanitized_email if sanitized_email else "general"  # Fallback if sanitization empties it
        else:
            prefix = "general"

        # Generate object key (overwrites if exists)
        # object_key = f"uploads/{prefix}_{file.filename}"
        object_key = f"uploads/{prefix}_input.xlsx"

        # Read file content into memory
        content = await file.read()

        # Upload to S3 (put_object overwrites existing keys by default)
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=object_key,
            Body=content
        )

        return {
            "status": "success",
            "file_name": file.filename,
            "s3_key": object_key
        }

    except (BotoCoreError, ClientError) as e:
        raise HTTPException(status_code=500, detail=f"S3 upload error: {str(e)}")
    

@router.post("/run-model-s3")
async def run_model_endpoint_s3(
    config_file: str = Form(..., description="Configuration file name for the ML model"),
    email: Optional[str] = Form(None, description="Optional user email address")
):
    try:
        if email:
            # Sanitize email: lowercase, replace non-alphanumeric with '_', remove leading/trailing '_'
            sanitized_email = ''.join(c if c.isalnum() else '_' for c in email.lower()).strip('_')
            prefix = sanitized_email if sanitized_email else "general"  # Fallback if sanitization empties it
        else:
            prefix = "general"

        # Generate input object key
        input_filename = f"{prefix}_input.xlsx"
        input_key = f"uploads/{input_filename}"

        # Download from S3
        try:
            s3_response = s3.get_object(Bucket=BUCKET_NAME, Key=input_key)
            content = s3_response['Body'].read()
            input_stream = BytesIO(content)
            df = pd.read_excel(input_stream)
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise HTTPException(
                    status_code=404,
                    detail=f"Input file not found in S3: {input_filename}. Please upload the file first and try again."
                )
            else:
                raise HTTPException(status_code=500, detail=f"S3 download error: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error reading input file from S3: {str(e)}")

        # Prepare dfs dict (compatible with original: key is filename)
        dfs = {input_filename: df}

        # Call the ML logic
        results = run_predictions(config_file=config_file, api_mode=True, building_data_dict=dfs)

        if not results or "error" in results:
            raise HTTPException(status_code=500, detail=results.get("error", "ML prediction failed"))

        # Parse results
        json_results = {k: json.loads(v) for k, v in results.items()}

        # Add execution time
        json_results["execution_time"] = datetime.utcnow().isoformat() + "Z"  # UTC ISO format

        # Generate output object key
        output_filename = f"{prefix}_output.json"
        output_key = f"uploads/{output_filename}"

        # Upload to S3
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=output_key,
            Body=json.dumps(json_results),
            ContentType="application/json"
        )

        return {
            "status": "success",
            "input_file": input_filename,
            "output_key": output_key
        }

    except (BotoCoreError, ClientError) as e:
        raise HTTPException(status_code=500, detail=f"S3 operation error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")    
    

@router.post("/down-result")
async def down_result(
    email: Optional[str] = Form(None, description="Optional user email address")
):
    """
    This endpoint accepts an optional email in the request body (form format),
    sanitizes it (or uses "general" if not provided),
    reads the corresponding result file from S3, and returns the predictions in JSON format.
    """

    if email is None:
        sanitized = "general"
    else:
        # Sanitize email: lowercase, replace non-alphanumeric characters with '_' for filename safety
        sanitized_email = ''.join(c if c.isalnum() else '_' for c in email.lower()).strip('_')
        sanitized = sanitized_email if sanitized_email else "general"  # Fallback if sanitization empties it

    # Define the S3 key for the result JSON
    output_key = f"results/{sanitized}_output.json"

    # Download from S3
    try:
        s3_response = s3.get_object(Bucket=BUCKET_NAME, Key=output_key)
        content = s3_response['Body'].read().decode('utf-8')
        json_results = json.loads(content)
        return JSONResponse(status_code=200, content=json_results)
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            raise HTTPException(
                status_code=404,
                detail=f"Result file not found in S3 for key: {output_key}. Please run the model first (and/or wait) and try again."
            )
        else:
            raise HTTPException(status_code=500, detail=f"S3 download error: {str(e)}")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Error parsing result file: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")



@router.post("/run-model")
async def run_model_endpoint(
    config_file: str = Form(...),
    files: List[UploadFile] = File(...)
):
    """
    This endpoint accepts a configuration file name and multiple Excel files,
    runs the ML model, and returns the predictions in JSON format.
    """
    # ... (file reading logic is the same) ...
    dfs: Dict[str, pd.DataFrame] = {}

    for file in files:
        contents = await file.read()
        input_stream = BytesIO(contents)
        try:
            dfs[file.filename] = pd.read_excel(input_stream)
        except Exception as e:
            return JSONResponse(status_code=400, content={"error": f"Error reading {file.filename}: {e}"})

    # Call the ML logic. 'results' is a dictionary of JSON strings.
    results = run_predictions(config_file=config_file, api_mode=True, building_data_dict=dfs)

    if not results or "error" in results:
        return JSONResponse(status_code=500, content=results)
        
    # The results are valid JSON strings, so we parse them back into
    # Python objects for a clean API response.
    json_results = {k: json.loads(v) for k, v in results.items()}

    # Pass the parsed Python objects to the response.
    return JSONResponse(status_code=200, content=json_results)
