# Project Horizon
<img src="docs/icon.png" style="width: 200px; border-radius: 20px;" alt="icon">

Imagine a world where images are processed and transformed effortlessly in the cloud.  
**_Project Horizon_ is an image processing pipeline that optimize images uploaded by users, making them smaller and faster to load without sacrificing visual quality.**

# C hello-world!


<!-- init-toc -->
- [Project Horizon](#project-horizon)
- [C hello-world!](#c-hello-world!)
	- [System Requirements](#system-requirements)
		- [Functional Requirements](#functional-requirements)
		- [Non-Functional Requirements](#non-functional-requirements)
	- [System Design](#system-design)
	- [Balance between speed, storage, and image quality.](#balance-between-speed,-storage,-and-image-quality.)
		- [Benchmarks (Maximum image dimension: 1000 pixels)](#benchmarks-(maximum-image-dimension:-1000-pixels))
	- [How to deploy and run Project Horizon](#how-to-deploy-and-run-project-horizon)
		- [Deploy the infrastructure to AWS](#deploy-the-infrastructure-to-aws)
		- [CLI Usage](#cli-usage)
		- [HTTP API Usage](#http-api-usage)
		- [Delete the infrastructure](#delete-the-infrastructure)
	- [How to run unit tests](#how-to-run-unit-tests)
	- [CI/CD Pipeline](#ci/cd-pipeline)
<!-- end-toc -->

## System Requirements

### Functional Requirements
- The service is automatically triggered when an image is uploaded to a source storage. (eg an object storage).
- The service processes the image uploaded to the source storage and uploads it to a destination storage.
- The processed image must be lighter and faster to load.
- The system must ensure good quality of the processed images.

### Non-Functional Requirements
- The system ensures efficient image processing to minimize execution time and costs.
- The system includes basic error handling to ensure the robustness of your function.

## System Design
The architecture is easily deployable on AWS through CloudFormation. The system leverages S3 and Lambda services which are integrated through S3 events when a resource is uploaded to the source bucket.<br>
It can be used through the AWS CLI by uploading/downloading images directly from the S3 buckets.

<u>Development to enable the service through the HTTP protocol is a work in progress.</u>

CLI interaction example:<br>
<img src="docs/ph-cli.png" style="width: 400px;"/>

HTTP interaction example:<br>
<img src="docs/ph-http.png" style="width: 400px;"/>

## Balance between speed, storage, and image quality.
The system uses the [SixLabors.ImageSharp](https://docs.sixlabors.com/articles/imagesharp/index.html?tabs=tabid-1) library to manipulate images and is configured to balance storage efficiency and image quality.  
<br>
The maximum size of the optimized images is 1.000x1.000 pixels, and the Lanczos algorithm is used for downscaling, ensuring good image quality. You can configure it in the `appSettings.json` file by modifying the `MaxImageDimension` property.
<br><br>
To prevent memory issues on Lambda, the property `MaxImageSizeInBytes` in the `appSettings.json` file has been configured to set the maximum image size (in bytes) for processing. If a larger image is uploaded to the source storage bucket, it will not be processed by the Lambda.
<br><br>
As the conversion algorithm, WebP in Lossless mode has been used. WebP is a good choice because it offers efficient compression without compromising image quality and is supported by all major web browsers.

### Benchmarks (Maximum image dimension: 1000 pixels)
| Filename             | Original Dimension (pixels) | Original Size (MB) | Final Dimension (pixels) | Final Size (MB) | Lambda Billed Duration (ms) |
|----------------------|-----------------------------|--------------------|--------------------------|-----------------|-----------------------------|
| source_800_800.png   | 800x800                     | 1.3                | 800x800                  | 0.77            | 7228                        |
| source_1920_1080.png | 1920x1080                   | 3.9                | 1000x562                 | 0.70            | 7632                        |

## How to deploy and run Project Horizon
For deploying and running Project Horizon, you need to have:

- [An AWS account](https://aws.amazon.com/account/?nc1=h_ls)
- [AWS CLI configured](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html)

### Deploy the infrastructure to AWS
- From the root of the project run `./deploy.sh` (default region: `eu-central-1`, default env: `dev`)
- Example for a custom deployment `./deploy.sh us-west-2 prod`

### CLI Usage
- Upload an image on the source S3 bucket.
    - Run `aws s3 cp <local_path>/image_name.png s3://<YOUR_AWS_ACCOUNT_ID>-source-bucket`
- Download the optimized image from the destination S3 bucket.
    - Run `aws s3 cp s3://<YOUR_AWS_ACCOUNT_ID>-destination-bucket/image_name.webp <local_path> `

### HTTP API Usage
**1. Get a presigned URL to upload an image:**
```text
curl -X GET https://<API_GATEWAY_URL>/prod/presigned-url
```

Response:
```json
{
    "imageId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "uploadUrl": "https://s3.../presigned-url"
}
```

**2. Upload your image using the presigned URL:**
```text
curl -X PUT "<UPLOAD_URL_FROM_RESPONSE>" \
-H "Content-Type: image/png" \
--data-binary @your-image.png
```

**3. Get information and presigned URL to download the optimized image:**
```text
curl -X GET https://<API_GATEWAY_URL>/prod/optimized-image/{imageId}
```

Response:
```json
{
    "imageId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "status": "Success",
    "url": "https://s3.../optimized-image-presigned-url",
    "dateTime": "2025-11-26T13:02:32.123Z"
}
```

**4. Download the optimized image:**
```text
curl -X GET "<DOWNLOAD_URL_FROM_RESPONSE>" \
-o optimized-image.webp
```

There are some images provided for you inside the `SourceImages` folder.

### Delete the infrastructure
- From the root of the project run `./delete.sh` (default region: `eu-central-1`, default env: `dev`)

## How to run unit tests
- Run `dotnet test`

## CI/CD Pipeline
This project uses GitHub Actions for Continuous Integration and Continuous Deployment.

- **CI**: Every push to the `main` branch and every pull request trigger automated tests, ensuring the code compiles successfully and all tests pass.
- **CD**: WIP
