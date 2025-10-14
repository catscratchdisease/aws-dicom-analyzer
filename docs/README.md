# Documentation

Additional documentation and guides for the AWS DICOM Image Analysis System.

## Documentation Structure

```
docs/
├── README.md                    # This file
├── deployment.md                # Deployment strategies
├── architecture.md              # Detailed architecture
├── api-reference.md             # API documentation
└── troubleshooting.md           # Common issues and solutions
```

## Quick Links

- **Getting Started**: See main [README.md](../README.md)
- **Setup Guide**: See [infrastructure/setup-guide.md](../infrastructure/setup-guide.md)
- **Lambda Functions**: See [lambda/README.md](../lambda/README.md)
- **Frontend**: See [frontend/README.md](../frontend/README.md)
- **Lambda Layers**: See [layers/README.md](../layers/README.md)

## Available Documentation

### 1. Deployment Guide (deployment.md)
- CI/CD setup with GitHub Actions
- Blue-green deployments
- Rollback procedures
- Environment management (dev/staging/prod)

### 2. Architecture Deep Dive (architecture.md)
- Detailed component diagrams
- Data flow explanation
- Scaling considerations
- Security architecture

### 3. API Reference (api-reference.md)
- Complete API endpoint documentation
- Request/response examples
- Error codes
- Authentication (if implemented)

### 4. Troubleshooting Guide (troubleshooting.md)
- Common errors and solutions
- Debugging techniques
- Performance optimization
- Cost optimization

## System Overview

### What This System Does

1. **Accepts uploads** of regular images (JPG/PNG) or DICOM medical images
2. **Processes images** with AWS Rekognition for object detection
3. **Converts DICOM** files to viewable format automatically
4. **Returns results** with detected objects and confidence scores

### Key Technologies

- **AWS Services**: Lambda, S3, DynamoDB, API Gateway, Rekognition
- **Languages**: Python 3.12, JavaScript (ES6+)
- **Libraries**: pydicom, Pillow, NumPy, Cornerstone.js
- **Architecture**: Serverless, event-driven

## Learning Resources

### AWS Documentation
- [AWS Lambda](https://docs.aws.amazon.com/lambda/)
- [Amazon S3](https://docs.aws.amazon.com/s3/)
- [Amazon DynamoDB](https://docs.aws.amazon.com/dynamodb/)
- [Amazon Rekognition](https://docs.aws.amazon.com/rekognition/)
- [API Gateway](https://docs.aws.amazon.com/apigateway/)

### DICOM Resources
- [pydicom Documentation](https://pydicom.github.io/)
- [DICOM Standard](https://www.dicomstandard.org/)
- [Cornerstone.js](https://cornerstonejs.org/)

### Best Practices
- [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)
- [Serverless Application Lens](https://docs.aws.amazon.com/wellarchitected/latest/serverless-applications-lens/welcome.html)
- [Lambda Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)

## Tutorials

### Basic Tutorials

**1. Deploy Your First Image**
```bash
# Follow setup guide
cd infrastructure
cat setup-guide.md

# Deploy
# ... follow steps

# Test with sample image
curl -X POST https://YOUR-API/request-upload \
  -d '{"fileName":"test.jpg","fileType":"image/jpeg"}'
```

**2. Process a DICOM File**
```bash
# Build layer with DICOM support
cd layers
./build-layer.sh

# Deploy layer and attach to Lambda 2
# Upload DICOM via web interface
```

### Advanced Tutorials

**3. Custom Object Detection**
- Train custom Rekognition model
- Integrate with Lambda function
- Update frontend to display custom labels

**4. Add User Authentication**
- Set up AWS Cognito
- Add authentication to API Gateway
- Update frontend with login flow

**5. Implement Caching**
- Add CloudFront distribution
- Enable API response caching
- Implement client-side caching

## Architecture Decisions

### Why Serverless?
- **Auto-scaling**: Handles traffic spikes automatically
- **Cost-effective**: Pay only for what you use
- **Maintenance-free**: No servers to manage
- **High availability**: Built-in redundancy

### Why Separate Buckets?
- **Security**: Different access policies
- **Organization**: Clearer separation of concerns
- **Performance**: Optimized for different access patterns

### Why Client-Side DICOM Viewer?
- **Instant preview**: No waiting for server conversion
- **Reduced costs**: Less Lambda invocations
- **Better UX**: Interactive viewer controls
- **Fallback**: Server conversion available if client fails

## FAQs

### Q: Can I use this in production?
**A:** Yes, but consider:
- Add authentication
- Implement rate limiting
- Enable monitoring/alerting
- Review security best practices

### Q: How much does it cost?
**A:** Typical costs:
- S3: ~$0.023/GB storage
- Lambda: ~$0.20 per 1M requests
- Rekognition: ~$1 per 1,000 images
- DynamoDB: Free tier covers most use cases

For 1,000 images/month: ~$5-10/month

### Q: What are the limits?
**A:**
- Max image size: 5 MB (Rekognition limit)
- Max Lambda timeout: 15 minutes
- Max DynamoDB item size: 400 KB
- S3 presigned URL expiry: 1 hour (configurable)

### Q: Can I process video?
**A:** Not out of the box, but can be extended:
- Use Rekognition Video APIs
- Process video frames
- Store results differently

### Q: Is this HIPAA compliant?
**A:** No, requires additional steps:
- Sign AWS BAA (Business Associate Agreement)
- Enable encryption at rest everywhere
- Implement audit logging
- Add access controls
- Review HIPAA requirements

## Contributing to Documentation

### Documentation Standards
- Use Markdown formatting
- Include code examples
- Add diagrams where helpful
- Keep language clear and concise
- Update when code changes

### How to Contribute
1. Fork repository
2. Create documentation branch
3. Make improvements
4. Submit pull request
5. Request review

## Support & Community

### Getting Help
- GitHub Issues: Report bugs or request features
- Discussions: Ask questions, share ideas
- AWS Support: For AWS-specific issues

### Useful Commands

**View all Lambda functions:**
```bash
aws lambda list-functions --query 'Functions[*].[FunctionName,Runtime,Timeout]'
```

**Check API Gateway endpoints:**
```bash
aws apigatewayv2 get-apis --query 'Items[*].[Name,ApiEndpoint]'
```

**Monitor costs:**
```bash
aws ce get-cost-and-usage \
  --time-period Start=2025-10-01,End=2025-10-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=SERVICE
```

## Changelog

See [CHANGELOG.md](../CHANGELOG.md) for version history and updates.

## License

MIT License - See [LICENSE](../LICENSE) for details.