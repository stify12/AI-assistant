# Implementation Plan

- [x] 1. Set up project structure and core data models



  - [x] 1.1 Create knowledge agent module directory structure

    - Create `knowledge_agent/` directory with `__init__.py`, `models.py`, `services.py`, `tools.py`, `agent.py`
    - _Requirements: 2.2, 5.1_

  - [x] 1.2 Implement core data models

    - Create `DifficultyLevel`, `QuestionType` enums
    - Create `KnowledgePoint`, `ParsedQuestion`, `SimilarQuestion`, `DedupeResult`, `TaskProgress` dataclasses
    - Implement JSON serialization/deserialization methods
    - _Requirements: 2.2, 2.6, 2.7, 5.1, 5.2_
  - [x] 1.3 Write property test for data serialization round-trip


    - **Property 9: Data Serialization Round-Trip**
    - **Validates: Requirements 5.3**

  - [x] 1.4 Write unit tests for data models

    - Test enum values
    - Test dataclass creation and validation
    - _Requirements: 2.2_

- [x] 2. Implement validation and similarity services



  - [x] 2.1 Implement image validation service
    - Create `validate_image_format()` function for JPG/PNG/JPEG validation
    - Create `validate_image_size()` function for 10MB limit
    - _Requirements: 1.2, 1.3_
  - [x] 2.2 Write property test for image format validation

    - **Property 1: Image Upload Validation**
    - **Validates: Requirements 1.2**
  - [x] 2.3 Implement similarity service

    - Create `SimilarityService` class
    - Implement `calculate_similarity()` using text embedding or simple algorithm
    - Implement `find_duplicates()` with configurable threshold
    - _Requirements: 8.1, 8.2_


  - [x] 2.4 Write property test for similarity threshold consistency
    - **Property 11: Similarity Threshold Consistency**
    - **Validates: Requirements 8.1, 8.2**

- [x] 3. Checkpoint - Ensure all tests pass


  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Implement model service and LangChain tools


  - [x] 4.1 Implement model service
    - Create `ModelService` class
    - Implement `get_available_models()` returning multimodal and text generation models
    - Implement `call_multimodal()` for vision model API calls
    - Implement `call_text_generation()` for text model API calls

    - _Requirements: 9.1, 9.2, 9.5_
  - [x] 4.2 Implement ImageParserTool
    - Create LangChain tool for parsing homework images

    - Extract question content, subject, type, difficulty
    - _Requirements: 2.1, 2.2, 2.6, 2.7_
  - [x] 4.3 Implement KnowledgeExtractorTool
    - Create LangChain tool for extracting knowledge points
    - Ensure primary knowledge point ≤ 20 characters
    - Build knowledge hierarchy with primary and secondary levels
    - _Requirements: 2.3, 2.8_
  - [x] 4.4 Write property test for knowledge point length constraint

    - **Property 2: Knowledge Point Length Constraint**
    - **Validates: Requirements 2.3**

  - [x] 4.5 Write property test for knowledge hierarchy structure
    - **Property 4: Knowledge Hierarchy Structure**

    - **Validates: Requirements 2.8**
  - [x] 4.6 Implement QuestionGeneratorTool
    - Create LangChain tool for generating similar questions
    - Preserve difficulty level and question type from original
    - Generate answer and solution steps
    - _Requirements: 3.3, 3.5, 3.6, 3.7_

  - [x] 4.7 Write property test for similar question attribute preservation
    - **Property 6: Similar Question Attribute Preservation**

    - **Validates: Requirements 3.5, 3.6**
  - [x] 4.8 Write property test for similar question output completeness

    - **Property 7: Similar Question Output Completeness**
    - **Validates: Requirements 3.7**

- [x] 5. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement HomeworkAgent and workflow
  - [x] 6.1 Implement HomeworkAgent class
    - Create agent with configurable multimodal and text models
    - Implement `parse_images()` for batch image processing
    - Implement `dedupe_knowledge_points()` for deduplication
    - Implement `generate_similar_questions()` for question generation
    - _Requirements: 2.1, 3.1, 3.2_
  - [x] 6.2 Write property test for knowledge point deduplication
    - **Property 5: Knowledge Point Deduplication**
    - **Validates: Requirements 3.2**
  - [x] 6.3 Write property test for question generation count constraint
    - **Property 8: Question Generation Count Constraint**
    - **Validates: Requirements 3.8**
  - [x] 6.4 Implement task progress tracking
    - Create progress tracking for image parsing and question generation
    - _Requirements: 6.1, 6.2_

- [x] 7. Implement Excel export service
  - [x] 7.1 Implement ExcelService class
    - Create `export_parse_result()` with required columns
    - Create `export_similar_questions()` with required columns
    - Create `export_full_result()` with all columns
    - Use openpyxl for xlsx format
    - _Requirements: 2.5, 2.9, 3.4, 3.9, 4.1, 4.2, 4.4, 4.5_
  - [x] 7.2 Write property test for Excel export column completeness
    - **Property 10: Excel Export Column Completeness**
    - **Validates: Requirements 2.9, 3.9, 4.2**
  - [x] 7.3 Implement dedupe result export
    - Export with columns: original point, merged point, similarity score, is_merged
    - _Requirements: 8.5_

- [x] 8. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Implement storage and configuration service
  - [x] 9.1 Implement StorageService
    - Create task storage with JSON files
    - Implement save and load operations
    - _Requirements: 5.1, 5.2_
  - [x] 9.2 Implement model preference persistence
    - Save user's model selection
    - Load saved preference on startup
    - _Requirements: 9.3, 9.4_
  - [x] 9.3 Write property test for model preference persistence
    - **Property 12: Model Preference Persistence**
    - **Validates: Requirements 9.3, 9.4**
  - [x] 9.4 Implement user edit persistence
    - Save user modifications to similar questions
    - Update export data with edits
    - _Requirements: 7.5_
  - [x] 9.5 Write property test for user edit persistence
    - **Property 13: User Edit Persistence**
    - **Validates: Requirements 7.5**

- [x] 10. Implement Flask API routes
  - [x] 10.1 Create knowledge agent blueprint
    - Create `/knowledge-agent` page route
    - _Requirements: 10.1, 10.2_
  - [x] 10.2 Implement upload API
    - `POST /api/knowledge-agent/upload` for image upload
    - Validate format and size
    - Return uploaded image list
    - _Requirements: 1.1, 1.2, 1.3, 1.4_
  - [x] 10.3 Implement parse API
    - `POST /api/knowledge-agent/parse` for image parsing
    - Return structured data with progress
    - _Requirements: 2.1, 2.2, 6.1_
  - [x] 10.4 Implement dedupe API
    - `POST /api/knowledge-agent/dedupe` for knowledge point deduplication
    - Support threshold configuration
    - _Requirements: 3.2, 8.1, 8.2, 8.4_
  - [x] 10.5 Implement generate API
    - `POST /api/knowledge-agent/generate` for similar question generation
    - Support count parameter
    - _Requirements: 3.1, 3.3, 3.8_
  - [x] 10.6 Implement export APIs
    - `GET /api/knowledge-agent/export/<type>` for Excel export
    - Support parse_result, similar_questions, full_result types
    - _Requirements: 4.1, 4.4_
  - [x] 10.7 Implement model selection APIs
    - `GET /api/knowledge-agent/models` for available models
    - `POST /api/knowledge-agent/models/select` for model selection
    - _Requirements: 9.1, 9.2, 9.3_
  - [x] 10.8 Implement regenerate API
    - `POST /api/knowledge-agent/regenerate` for single question regeneration
    - _Requirements: 7.4_

- [ ] 11. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 12. Implement frontend page and components
  - [x] 12.1 Create knowledge agent HTML template
    - Create `templates/knowledge-agent.html`
    - Implement step indicator component (5 steps)
    - Match main page styling
    - _Requirements: 10.3, 11.1, 11.2_
  - [x] 12.2 Implement image upload component
    - Multi-image upload with drag-and-drop
    - Image preview list
    - Format and size validation feedback
    - _Requirements: 1.1, 1.4, 11.5_
  - [x] 12.3 Implement parse result component
    - Result table with inline editing
    - Model selector for multimodal models
    - Progress indicator
    - _Requirements: 2.5, 9.1, 11.6_
  - [x] 12.4 Implement knowledge point confirmation component
    - Dedupe result display with checkboxes
    - Similarity threshold slider
    - Manual merge confirmation
    - _Requirements: 8.3, 11.7_
  - [x] 12.5 Implement question generation component
    - Model selector for text generation models
    - Count selector (1-5)
    - Progress and real-time preview
    - Regenerate button for each question
    - _Requirements: 3.8, 7.4, 9.2, 11.8_
  - [x] 12.6 Implement export component
    - Export type selection (parse/similar/full)
    - Download buttons
    - _Requirements: 4.4, 11.9_

- [x] 13. Implement frontend JavaScript
  - [x] 13.1 Create knowledge agent JavaScript file
    - Create `static/js/knowledge-agent.js`
    - Implement step navigation logic
    - _Requirements: 11.2, 11.3, 11.4_
  - [x] 13.2 Implement API integration
    - Upload, parse, dedupe, generate, export API calls
    - Progress polling
    - Error handling and retry
    - _Requirements: 6.3_
  - [x] 13.3 Implement inline editing
    - Edit knowledge points and similar questions
    - Save edits to backend
    - _Requirements: 7.5_

- [x] 14. Implement frontend CSS
  - [x] 14.1 Create knowledge agent CSS file
    - Create `static/css/knowledge-agent.css`
    - Step indicator styling
    - Match main page color scheme and style
    - _Requirements: 10.3_

- [x] 15. Integrate with main page
  - [x] 15.1 Add navigation link to main page
    - Add "知识点类题" link in left sidebar footer
    - _Requirements: 10.1_
  - [x] 15.2 Share configuration with main page
    - Reuse API settings from main page
    - _Requirements: 10.5_

- [x] 16. Final Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
