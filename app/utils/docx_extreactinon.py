import docx

def extract_docx_text(docx_path):
    # Load the .docx file
    doc = docx.Document(docx_path)
    
    # Initialize variables
    full_text = []
    current_heading = None
    
    # Access the document's XML to process elements in order
    doc_element = doc.element.body
    
    # Iterate through all elements in the document body
    for elem in doc_element:
        # Handle paragraphs
        if elem.tag.endswith('p'):  # Paragraph element
            para = doc.paragraphs[[p._element for p in doc.paragraphs].index(elem)]
            text = para.text.strip()
            if not text:
                continue
                
            # Check if the paragraph is a heading (based on style or bold formatting)
            if para.style.name.startswith('Heading') or (para.runs and any(run.bold for run in para.runs)):
                if current_heading and full_text and full_text[-1] != '':
                    full_text.append('')
                current_heading = text
                full_text.append(text + ':')
            else:
                if text:
                    full_text.append(text)
                    if full_text[-1] != '':
                        full_text.append('')
        
        # Handle tables
        elif elem.tag.endswith('tbl'):  # Table element
            table = doc.tables[[t._element for t in doc.tables].index(elem)]
            for row in table.rows:
                row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_text:
                    full_text.append(' | '.join(row_text))
                    full_text.append('')
    
    # Extract text from footers (if any)
    for section in doc.sections:
        for footer in section.footer.paragraphs:
            text = footer.text.strip()
            if text:
                full_text.append(text)
                full_text.append('')
    
    # Clean up excessive blank lines
    cleaned_text = []
    last_was_empty = False
    for line in full_text:
        if line.strip():
            cleaned_text.append(line)
            last_was_empty = False
        elif not last_was_empty:
            cleaned_text.append('')
            last_was_empty = True
    
    return '\n'.join(cleaned_text).rstrip()