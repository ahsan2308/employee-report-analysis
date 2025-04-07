# Model Modification Guide

This guide explains how to modify data models in the application and what changes need to be made across different files to maintain compatibility.

## Modifying the EmployeeAnalysis Model

The `EmployeeAnalysis` model appears in multiple places that must stay in sync:

1. **Database Model**: `app/models/db_models.py`
2. **Pydantic Schema**: `app/schemas/analysis_schema.py`
3. **LLM Structured Model**: `app/models/structured_models_llm.py`

### Step 1: Modify the Database Model

When adding fields to the `EmployeeAnalysis` database model:

```python
# In db_models.py
class EmployeeAnalysis(Base):
    # ... existing fields ...
    
    # Add your new field
    new_field = Column(String, nullable=True)
    
    # ... other fields ...
```

### Step 2: Update the API Schema

The Pydantic schemas (inside the schemas folder) need to be updated to include new fields for API requests/responses:

```python
# In analysis_schema.py
class EmployeeAnalysisCreate(BaseModel):
    # ... existing fields ...
    new_field: Optional[str] = None

class EmployeeAnalysisResponse(BaseModel):
    # ... existing fields ...
    new_field: Optional[str] = None
```

### Step 3: Update the LLM Output Format

The LLM needs to know how to structure its output to match your model:

```python
# In structured_models_llm.py
class EmployeeAnalysis(BaseModel):
    # ... existing fields ...
    new_field: str = Field(description="Description of the new field")
```

### Step 4: Update Related Services

If you added structured fields that should be extracted from LLM outputs:

1. **Update the Analysis Service** (`app/services/analysis_service.py`):
   ```python
   def create_analysis_from_llm_output(result, report_id, employee_id):
       # ... existing code ...
       analysis.new_field = result.get("new_field")
   ```

2. **Update LLM Prompts** if needed (`app/prompts/structured_prompts.py`):
   ```python
   def employee_analysis_prompt():
       # Include guidance about the new field in the prompt
   ```

## Switching Between Simple and Full Models

The codebase includes both simplified and full-featured versions of models.

### To use the simplified version:

1. Ensure `db_models.py` has only the core fields uncommented
2. Ensure `analysis_schema.py` has only the core fields
3. Use the simplified `EmployeeAnalysis` class in `structured_models_llm.py`

### To use the full-featured version:

1. Uncomment the additional fields in `db_models.py`
2. Uncomment the additional fields in `analysis_schema.py`
3. Use the full `FullEmployeeAnalysis` class (rename to `EmployeeAnalysis`) in `structured_models_llm.py`

## Impacts on Other Components

When modifying models, consider these dependencies:

1. **LLM Service** (`app/services/llm_service.py`): 
   - The `analyze_report()` method references the Pydantic model

2. **Vector Store** (`app/services/vector_store_service.py`):
   - Query results might include additional fields

3. **API Endpoints** (`app/api/analyses.py`):
   - API responses will expose new fields

4. **Frontend** (if applicable):
   - UI components may need to display new fields

## Database Migrations

After changing the database models, you'll need to create and run migrations:

```bash
alembic revision --autogenerate -m "Add new field to EmployeeAnalysis"
alembic upgrade head
```

Remember that you cannot remove a non-nullable column without a migration strategy.

## Testing Changes

Always test all components after model changes:

1. Database operations (CRUD)
2. LLM analysis with the new model
3. API endpoints for correct data representation
4. Any frontend components that display the model data
