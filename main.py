import functions_framework
import camelot
import json
import tempfile
import os
import base64
from flask import jsonify

@functions_framework.http
def extract_tables(request):
    """Cloud Function to extract tables from PDF using Camelot"""
    
    # Enable CORS
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)
    
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Content-Type': 'application/json'
    }
    
    try:
        request_json = request.get_json(silent=True)
        
        if not request_json:
            return (jsonify({
                'success': False,
                'error': 'No JSON data provided',
                'tables_count': 0,
                'tables_data': []
            }), 400, headers)
        
        pdf_base64 = request_json.get('pdf_base64')
        filename = request_json.get('filename', 'document.pdf')
        
        if not pdf_base64:
            return (jsonify({
                'success': False,
                'error': 'pdf_base64 field is required',
                'tables_count': 0,
                'tables_data': []
            }), 400, headers)
        
        try:
            pdf_content = base64.b64decode(pdf_base64)
        except Exception as e:
            return (jsonify({
                'success': False,
                'error': f'Invalid base64 encoding: {str(e)}',
                'tables_count': 0,
                'tables_data': []
            }), 400, headers)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(pdf_content)
            tmp_path = tmp_file.name
        
        try:
            tables_data = []
            
            print(f"Processing: {filename}")
            
            tables_lattice = camelot.read_pdf(
                tmp_path,
                flavor='lattice',
                pages='all',
                line_scale=40
            )
            
            print(f"Found {len(tables_lattice)} lattice tables")
            
            for i, table in enumerate(tables_lattice):
                accuracy = table.parsing_report.get('accuracy', 0)
                
                if accuracy > 75:
                    csv_data = table.df.to_csv(index=False, encoding='utf-8')
                    
                    tables_data.append({
                        'table_index': len(tables_data) + 1,
                        'page': table.parsing_report.get('page', 0),
                        'accuracy': round(accuracy, 2),
                        'method': 'lattice',
                        'rows': table.shape[0],
                        'columns': table.shape[1],
                        'csv_data': csv_data,
                        'preview': csv_data.split('\n')[:5]
                    })
                    
                    print(f"Table {len(tables_data)}: {table.shape[0]}x{table.shape[1]} ({accuracy:.1f}%)")
            
            if len(tables_lattice) == 0:
                print("Trying stream method...")
                
                tables_stream = camelot.read_pdf(
                    tmp_path,
                    flavor='stream',
                    pages='all',
                    edge_tol=50
                )
                
                print(f"Found {len(tables_stream)} stream tables")
                
                for i, table in enumerate(tables_stream):
                    csv_data = table.df.to_csv(index=False, encoding='utf-8')
                    
                    tables_data.append({
                        'table_index': len(tables_data) + 1,
                        'page': table.parsing_report.get('page', 0),
                        'accuracy': 90,
                        'method': 'stream',
                        'rows': table.shape[0],
                        'columns': table.shape[1],
                        'csv_data': csv_data,
                        'preview': csv_data.split('\n')[:5]
                    })
            
            result = {
                'success': True,
                'tables_count': len(tables_data),
                'tables_data': tables_data,
                'filename': filename
            }
            
            print(f"Extraction complete: {len(tables_data)} tables found")
            
            return (jsonify(result), 200, headers)
            
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return (jsonify({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__,
            'tables_count': 0,
            'tables_data': []
        }), 500, headers)
