package com.example.demo.controller;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.presigner.S3Presigner;
import software.amazon.awssdk.services.s3.model.PutObjectRequest;
import software.amazon.awssdk.services.s3.presigner.model.GetObjectPresignRequest;
import software.amazon.awssdk.services.s3.model.GetObjectRequest;
import software.amazon.awssdk.core.sync.RequestBody;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.MediaType;
import org.springframework.web.multipart.MaxUploadSizeExceededException;
import org.springframework.web.multipart.MultipartException;

import java.time.Duration;
import java.util.*;
import java.nio.charset.StandardCharsets;

@RestController
@CrossOrigin(
    origins = {
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://localhost:5173"
    },
    allowCredentials = "true"
)
public class UploadController {
    private static final Logger logger = LoggerFactory.getLogger(UploadController.class);

    private final S3Client s3Client;
    private final S3Presigner presigner;

    @Value("${aws.s3.bucket-name}")
    private String bucketName;

    public UploadController(S3Client s3Client, S3Presigner presigner) {
        this.s3Client = s3Client;
        this.presigner = presigner;
    }

    @PostMapping(value = "/upload", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<?> uploadFiles(@RequestParam("files") List<MultipartFile> files) {
        try {
            if (files == null || files.isEmpty()) {
                logger.error("No files received in the request");
                return ResponseEntity.badRequest().body("No files were uploaded");
            }

            logger.info("Received upload request with {} files", files.size());
            List<String> presignedUrls = new ArrayList<>();

            for (MultipartFile file : files) {
                if (file.isEmpty()) {
                    logger.warn("Received empty file, skipping");
                    continue;
                }

                String key = file.getOriginalFilename();
                if (key == null || key.trim().isEmpty()) {
                    logger.warn("Received file with no name, skipping");
                    continue;
                }

                logger.info("Processing file: {} (size: {} bytes)", key, file.getSize());

                try {
                    // Upload the file
                    logger.info("Uploading file to S3 bucket: {}", bucketName);
                    s3Client.putObject(
                            PutObjectRequest.builder()
                                    .bucket(bucketName)
                                    .key(key)
                                    .contentType(file.getContentType())
                                    .build(),
                            RequestBody.fromBytes(file.getBytes())
                    );
                    logger.info("File uploaded successfully to S3");

                    // Generate the presigned GET URL
                    GetObjectRequest getObjectRequest = GetObjectRequest.builder()
                            .bucket(bucketName)
                            .key(key)
                            .build();

                    GetObjectPresignRequest presignRequest = GetObjectPresignRequest.builder()
                            .signatureDuration(Duration.ofMinutes(30))
                            .getObjectRequest(getObjectRequest)
                            .build();

                    String presignedUrl = presigner.presignGetObject(presignRequest).url().toString();
                    logger.info("Generated presigned URL for {}: {}", key, presignedUrl);

                    presignedUrls.add(presignedUrl);
                } catch (Exception e) {
                    logger.error("Error processing file {}: {}", key, e.getMessage(), e);
                    return ResponseEntity.status(500)
                            .body("Error processing file " + key + ": " + e.getMessage());
                }
            }

            if (presignedUrls.isEmpty()) {
                logger.warn("No files were successfully processed");
                return ResponseEntity.badRequest().body("No files were successfully processed");
            }

            logger.info("Upload process completed successfully");
            return ResponseEntity.ok(presignedUrls);

        } catch (MaxUploadSizeExceededException e) {
            logger.error("File size exceeds maximum limit", e);
            return ResponseEntity.status(413).body("File size exceeds maximum limit of 50MB");
        } catch (MultipartException e) {
            logger.error("Error processing multipart request", e);
            return ResponseEntity.status(400).body("Error processing multipart request: " + e.getMessage());
        } catch (Exception e) {
            logger.error("Upload failed", e);
            return ResponseEntity.status(500).body("Upload failed: " + e.getMessage());
        }
    }
}
