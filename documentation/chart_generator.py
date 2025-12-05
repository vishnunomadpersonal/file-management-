"""
Mermaid Diagram Generator for File Management System Architecture
Generates a clean Mermaid flowchart showing the layered architecture
"""

def generate_mermaid_diagram():
    """Generate a Mermaid diagram for the file management system architecture"""
    
    mermaid_content = """graph TD
    A["FRONTEND<br/>React/Next.js<br/>User Interface • HTTP Requests • State Management"] --> |"HTTP/JSON"| B["API ROUTES<br/>FastAPI Endpoints<br/>Route Handlers • Request/Response DTOs • HTTP Validation"]
    B --> |"DTOs"| C["HANDLERS<br/>Business Coordination<br/>Logic Coordination • DTO Transformations • Error Handling"]
    C --> |"DTOs"| D["SERVICES<br/>Core Business Logic<br/>Business Rules • External Integrations • MinIO & Celery"]
    D --> |"Entities/DTOs"| E["REPOSITORIES<br/>Data Access Layer<br/>Database Operations • Entity Conversion • Query Logic"]
    E --> |"SQL/ORM"| F["DATABASE<br/>MySQL Storage<br/>Persistent Storage • Entity Models • Foreign Key Relations"]

    %% Styling for each layer
    classDef frontend fill:#667EEA,stroke:#fff,stroke-width:3px,color:#fff,font-weight:bold
    classDef api fill:#48BB78,stroke:#fff,stroke-width:3px,color:#fff,font-weight:bold
    classDef handlers fill:#ED8936,stroke:#fff,stroke-width:3px,color:#fff,font-weight:bold
    classDef services fill:#9F7AEA,stroke:#fff,stroke-width:3px,color:#fff,font-weight:bold
    classDef repositories fill:#38B2AC,stroke:#fff,stroke-width:3px,color:#fff,font-weight:bold
    classDef database fill:#4A5568,stroke:#fff,stroke-width:3px,color:#fff,font-weight:bold

    %% Apply styles to nodes
    class A frontend
    class B api
    class C handlers
    class D services
    class E repositories
    class F database

    %% Add title and subtitle as subgraph
    subgraph Title ["File Management System Architecture - Clean Architecture with DTO Pattern"]
        direction TB
        G[" "]
    end
    
    %% Style the title subgraph
    classDef titleStyle fill:#F7FAFC,stroke:#2D3748,stroke-width:2px,color:#2D3748,font-weight:bold
    class Title titleStyle
    
    %% Hide the placeholder node
    classDef hidden fill:transparent,stroke:transparent,color:transparent
    class G hidden"""

    return mermaid_content

def save_mermaid_file():
    """Save the Mermaid diagram to a file"""
    diagram_content = generate_mermaid_diagram()
    
    # Save to .mmd file
    with open('file_management_architecture.mmd', 'w', encoding='utf-8') as f:
        f.write(diagram_content)
    
    print("✅ Mermaid diagram saved as 'file_management_architecture.mmd'")
    print("\n📋 To render this diagram:")
    print("1. Copy the content and paste it into https://mermaid.live/")
    print("2. Or use Mermaid CLI: mermaid -i file_management_architecture.mmd -o architecture.png")
    print("3. Or view it in any Markdown viewer that supports Mermaid")
    
    # Also create a markdown file with the diagram
    markdown_content = f"""# File Management System Architecture

## Clean Architecture with DTO Pattern

```mermaid
{diagram_content}
```

## Key Architecture Principles

- **DTOs**: Data validation & transformation between layers
- **Clean separation of concerns**: Each layer has specific responsibilities  
- **Security through controlled data flow**: Input validation and controlled exposure
- **Scalable layered architecture**: Easy to maintain and extend

## Layer Responsibilities

### Frontend (React/Next.js)
- User interface components
- HTTP request handling
- Client-side state management

### API Routes (FastAPI)
- HTTP endpoint definitions
- Request/Response DTOs
- Input validation and serialization

### Handlers
- Business logic coordination
- DTO transformations between layers
- Error handling and response formatting

### Services
- Core business logic implementation
- External service integrations (MinIO, Celery)
- Business rule enforcement

### Repositories
- Database operations and queries
- Entity to DTO conversion
- Data access abstraction

### Database (MySQL)
- Persistent data storage
- Entity models with SQLAlchemy
- Foreign key relationships and constraints
"""
    
    with open('architecture_documentation.md', 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    
    print("✅ Documentation saved as 'architecture_documentation.md'")

if __name__ == "__main__":
    save_mermaid_file()