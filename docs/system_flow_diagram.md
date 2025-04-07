# Employee Report Analysis System Flow

```mermaid
graph TD
    subgraph Client
        A[Frontend/Client] --> B[API Request]
    end

    subgraph API_Layer["API Layer (FastAPI)"]
        B --> C1[Employee Endpoints]
        B --> C2[Report Endpoints]
        B --> C3[Analysis Endpoints]
    end

    subgraph Database["Database Layer"]
        C1 --> D1[Employee Data]
        C2 --> D2[Report Data]
        D2 --> D3[QdrantMapping]
    end

    subgraph Vector_Store["Vector Store (Qdrant)"]
        E1[Document Processing]
        E2[Embedding Generation]
        E3[Vector Storage]
        E4[Semantic Search]
        
        D2 --> E1
        E1 --> E2
        E2 --> E3
        E3 --> E4
    end

    subgraph LLM_Services["LLM Services (Ollama)"]
        F1[Report Analysis]
        F2[Structured Output Generation]
        F3[Sentiment Analysis]
        
        E4 --> F1
        F1 --> F2
        F1 --> F3
    end

    subgraph Results["Results"]
        F2 --> G1[Achievements]
        F2 --> G2[Challenges]
        F3 --> G3[Sentiment]
        F2 --> G4[Risk Assessment]
        F2 --> G5[Action Items]
    end

    G1 --> H[API Response]
    G2 --> H
    G3 --> H
    G4 --> H
    G5 --> H
    H --> A

    subgraph DataFlow["Data Processing Flow"]
        I1[1. Submit Report] --> I2[2. Store in Database]
        I2 --> I3[3. Generate Embeddings]
        I3 --> I4[4. Store in Vector DB]
        I4 --> I5[5. Semantic Search]
        I5 --> I6[6. LLM Analysis]
        I6 --> I7[7. Return Structured Results]
    end
```

## Detailed Process Flow

1. **Report Submission**
   - User submits employee report via API
   - System stores report in relational database (PostgreSQL/MSSQL)

2. **Vector Processing**
   - Report is chunked into smaller sections
   - Embedding vectors are generated for each chunk
   - Vectors are stored in Qdrant with metadata
   - Mappings between chunks and reports are stored in database

3. **Analysis Request**
   - User requests analysis for employee report(s)
   - System retrieves relevant report chunks using semantic search
   - Similar reports are identified for context

4. **LLM Processing**
   - Report and context are sent to Ollama LLM
   - LLM generates structured analysis with achievements, challenges, etc.
   - Results are formatted according to predefined schemas

5. **Result Delivery**
   - Structured analysis is returned to user via API
   - Results can include achievements, challenges, sentiment, risk levels, etc.
