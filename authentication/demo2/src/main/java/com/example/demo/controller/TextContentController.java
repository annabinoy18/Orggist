package com.example.demo.controller;

import com.example.demo.model.TextContent;
import com.example.demo.repository.TextContentRepository;
import org.springframework.web.bind.annotation.*;
import org.springframework.http.ResponseEntity;
import org.springframework.web.client.RestTemplate;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.HttpMethod;
import java.util.List;
import java.util.Map;
import java.util.HashMap;
import java.util.ArrayList;
import java.util.Arrays;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

@RestController
@RequestMapping("/code-upload")
public class TextContentController {
    private static final Logger logger = LoggerFactory.getLogger(TextContentController.class);
    private final TextContentRepository repository;
    private final RestTemplate restTemplate;
    private static final int CHUNK_SIZE = 1000; // Characters per chunk

    public TextContentController(TextContentRepository repository) {
        this.repository = repository;
        this.restTemplate = new RestTemplate();
    }

    private List<String> chunkText(String text) {
        List<String> chunks = new ArrayList<>();
        String[] words = text.split("\\s+");
        StringBuilder currentChunk = new StringBuilder();
        
        for (String word : words) {
            if (currentChunk.length() + word.length() + 1 > CHUNK_SIZE) {
                chunks.add(currentChunk.toString().trim());
                currentChunk = new StringBuilder();
            }
            currentChunk.append(word).append(" ");
        }
        
        if (currentChunk.length() > 0) {
            chunks.add(currentChunk.toString().trim());
        }
        
        return chunks;
    }

    @PostMapping
    public ResponseEntity<?> uploadText(@RequestBody TextContent text) {
        try {
            logger.info("Received text upload request for user: {}", text.getUsername());
            
            // First save to database
            TextContent savedText = repository.save(text);
            logger.info("Saved text to database with ID: {}", savedText.getId());
            
            // Split text into chunks if it's too large
            List<String> chunks = chunkText(savedText.getContent());
            logger.info("Split text into {} chunks", chunks.size());
            int successfulChunks = 0;
            
            for (int i = 0; i < chunks.size(); i++) {
                String chunk = chunks.get(i);
                // Add metadata to chunk
                String chunkWithMetadata = String.format("[%s - Chunk %d/%d] %s", 
                    savedText.getUsername(), i + 1, chunks.size(), chunk);
                
                // Create request for embedding
                Map<String, String> embeddingRequest = new HashMap<>();
                embeddingRequest.put("text", chunkWithMetadata);
                
                logger.info("Requesting embedding for chunk {}/{}", i + 1, chunks.size());
                
                // Get embedding from vector DB service
                ResponseEntity<Map<String, Object>> embeddingResponse = restTemplate.exchange(
                    "http://localhost:8000/get-embedding",
                    HttpMethod.POST,
                    new org.springframework.http.HttpEntity<>(embeddingRequest),
                    new ParameterizedTypeReference<Map<String, Object>>() {}
                );

                Map<String, Object> responseBody = embeddingResponse.getBody();
                if (embeddingResponse.getStatusCode().is2xxSuccessful() && responseBody != null && responseBody.get("embedding") != null) {
                    logger.info("Successfully received embedding for chunk {}/{}", i + 1, chunks.size());
                    
                    // Create request for vector DB storage
                    Map<String, Object> vectorDBRequest = new HashMap<>();
                    vectorDBRequest.put("content", chunkWithMetadata);  // Changed from "text" to "content" to match FastAPI model

                    // Store in vector DB
                    ResponseEntity<String> vectorDBResponse = restTemplate.postForEntity(
                        "http://localhost:8000/add-document",
                        vectorDBRequest,
                        String.class
                    );

                    if (vectorDBResponse.getStatusCode().is2xxSuccessful()) {
                        successfulChunks++;
                        logger.info("Successfully stored chunk {}/{} in vector DB", i + 1, chunks.size());
                    } else {
                        logger.error("Failed to store chunk {}/{} in vector DB. Status: {}", 
                            i + 1, chunks.size(), vectorDBResponse.getStatusCode());
                    }
                } else {
                    logger.error("Failed to get embedding for chunk {}/{}. Status: {}, Response: {}", 
                        i + 1, chunks.size(), embeddingResponse.getStatusCode(), responseBody);
                }
            }

            if (successfulChunks == chunks.size()) {
                logger.info("All chunks processed successfully");
                return ResponseEntity.ok(savedText);
            } else {
                String message = String.format(
                    "Text saved to database. %d/%d chunks successfully added to vector DB.", 
                    successfulChunks, chunks.size());
                logger.warn(message);
                return ResponseEntity.ok(message);
            }
        } catch (Exception e) {
            logger.error("Error processing text upload", e);
            return ResponseEntity.internalServerError()
                .body("Error processing text: " + e.getMessage());
        }
    }

    @GetMapping
    public List<TextContent> getAllText() {
        return repository.findAll();
    }
}
