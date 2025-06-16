package com.example.demo.repository;

import com.example.demo.model.TextContent;
import org.springframework.data.jpa.repository.JpaRepository;

public interface TextContentRepository extends JpaRepository<TextContent, Long> {
}
