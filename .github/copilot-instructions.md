The repository implements a small serverless AWS image-analysis system (including DICOM support). These instructions give an AI coding agent the targeted facts and patterns that help produce precise, low-risk edits and feature work.

Quick context
- Major components: `frontend/` (static single-file app `index.html`), `lambda/` (3 functions), `layers/` (build script for DICOM dependencies), and `infrastructure/` (IAM, CORS, setup docs).
- Core data flow: Frontend -> API Gateway -> Lambda1 (presigned PUT URL) -> S3 uploads -> S3 event -> Lambda2 (DICOM conversion + Rekognition) -> DynamoDB -> Lambda3 (results read) -> Frontend polling.

Key files to reference
- `frontend/index.html` — single-file SPA. Look here for API endpoint usage, polling behavior, and upload flow (search for `API_ENDPOINT`, `pollForResults`, and `request-upload`).
- `lambda/lambda1-generate-upload-url/lambda1-code.py` — generates presigned PUT URLs and creates a DynamoDB job item with: `jobId`, `status`, `s3Key`, `fileName`, `fileType`, `createdAt`.
- `lambda/lambda2-process-image/lambda2-code.py` — S3-triggered; checks file suffix (.dcm/.dicom) to detect DICOM, converts to JPEG using pydicom+Pillow, stores converted image to `converted/{jobId}/converted.jpg`, calls Rekognition.detect_labels, converts floats to Decimals before writing to DynamoDB, and sets `status` to `complete` (or `error`).
- `lambda/lambda3-get-results/lambda3-code.py` — HTTP GET handler that expects `?jobId=...` and returns {status, results, imageUrl, error}; converts DynamoDB Decimal types back to floats.
- `infrastructure/` & `layers/` — contain CORS, notification, IAM hints and the layer build script required to run DICOM code in Lambda.

Important conventions and patterns (do not break)
- S3 key layouts
  - Uploads are stored under: `uploads/{jobId}/{originalFileName}` (created by Lambda1).
  - DICOM-converted images are written under: `converted/{jobId}/converted.jpg` (Lambda2).
- DynamoDB schema
  - Primary key: `jobId` (UUID string)
  - Items include `status` (pending|complete|error), `results` (Rekognition response saved as numbers -> Decimal), `imageUrl` (optional presigned URL), `error` (optional string), timestamps: `createdAt`, `updatedAt`.
- API surface
  - POST /request-upload — body {fileName, fileType} → response {uploadUrl, jobId}
  - GET /get-results?jobId={id} — response {status, results, imageUrl, error}
- Error handling
  - Lambdas write an `error` string and set `status` = `error` on failure (Lambda2 attempts to update the item on exception). Keep updates idempotent and avoid double-writing unrelated attributes.
- Binary / content-type behavior
  - DICOM files may be uploaded with no or nonstandard MIME type; Lambda1 forces `application/dicom` when filename ends with `.dcm` or `.dicom`.
  - Rekognition expects regular images (JPEG/PNG). Lambda2 converts DICOM to JPEG and stores it before calling Rekognition.

Developer workflows and commands (verified in README files)
- Build/publish lambdas (zip + aws cli)
  - Package: `cd lambda/<fn>; zip function.zip <file>` then `aws lambda update-function-code --function-name <name> --zip-file fileb://function.zip`.
- Build Lambda layer for DICOM (requires Docker/linux lambda image)
  - See `layers/build-layer-script.sh` and README. The README uses the public ECR lambda python:3.12 image and installs `pydicom pillow numpy pylibjpeg*` into a `python/` folder then zips it.
- Deploy frontend
  - `aws s3 cp frontend/index.html s3://YOUR-WEBSITE-BUCKET/` + set static website hosting / bucket policy.
- Local testing
  - The Lambdas include small `python -c` snippets in their README to invoke `lambda_handler` directly for quick tests.

Concrete examples an agent can use when editing code
- When creating or updating S3 keys, follow the exact prefixes used above (`uploads/` and `converted/`) to maintain downstream assumptions.
- When updating DynamoDB writes, preserve use of Decimal for numeric values (see `convert_floats_to_decimals`) and reverse the conversion in the reader (see `convert_decimals_to_floats`).
- Polling behavior: frontend polls every 2 seconds by default and stops after `maxAttempts` (30) — changing backend latency should consider increasing `maxAttempts` or making polling configurable in `index.html`.

Integration points and environment variables
- Lambda env vars expected across the repo:
  - `UPLOAD_BUCKET` (Lambda1), `TABLE_NAME` (all three Lambdas)
- AWS services used: S3 (uploads + hosting), DynamoDB (results), Rekognition (labels), API Gateway (HTTP API), Lambda Layers (pydicom stack). IAM must grant S3/DynamoDB/Rekognition actions as described in `infrastructure/iam-policies.json`.

What to avoid or watch for
- Don't assume DICOM libraries are always available — Lambda2 uses a runtime check and will raise a clear error if pydicom isn't installed. If you add new dependencies, update the layer build and mention it in `layers/README.md`.
- Keep CORS headers in Lambda responses (handlers already set `Access-Control-Allow-Origin: '*'`); changing CORS behavior requires coordination with `infrastructure/s3-cors.json` and API Gateway stage settings.
- When modifying APIs, keep request/response shapes stable: `POST /request-upload` returns `uploadUrl` and `jobId`; `GET /get-results` returns status and results as described above.

If you need more context
- Open these files for the canonical behavior: `frontend/index.html`, `lambda/*/lambda*-code.py`, `infrastructure/setup-guide.md`, and `layers/build-layer-script.sh`.

If this file omitted anything useful or you'd like the agent to follow stricter rules (formatting, tests, or commit messages), tell me and I will iterate.
