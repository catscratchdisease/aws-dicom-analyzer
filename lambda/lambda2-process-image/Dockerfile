FROM public.ecr.aws/lambda/python:3.12

# Install system dependencies
RUN dnf install -y libgomp && dnf clean all

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy Lambda function code
COPY lambda2-code.py ${LAMBDA_TASK_ROOT}/

# Copy inference module
COPY inference/ ${LAMBDA_TASK_ROOT}/inference/

# Copy model file
COPY models/ ${LAMBDA_TASK_ROOT}/models/

# Set the CMD to your handler
CMD ["lambda2-code.lambda_handler"]
