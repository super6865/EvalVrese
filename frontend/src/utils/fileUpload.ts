/**
 * File upload utilities - Based on coze-loop implementation
 */
import * as XLSX from 'xlsx'
import JSZip from 'jszip'

/**
 * Get CSV headers from file (frontend only)
 * Uses multiple encoding attempts to handle different file encodings
 */
export const getCSVHeaders = (file: File): Promise<string[]> => {
  return new Promise((resolve, reject) => {
    const tryRead = (encoding: string = 'UTF-8') => {
      const reader = new FileReader();
      
      reader.onload = function (e) {
        const text = e.target?.result as string;
        if (!text) {
          if (encoding === 'UTF-8') {
            // Try GBK if UTF-8 fails
            tryRead('GBK');
            return;
          }
          reject(new Error('Failed to read file'));
          return;
        }
        
        const lines = text.split(/\r?\n/);
        if (lines.length === 0) {
          resolve([]);
          return;
        }
        
        // Parse first line as CSV headers
        const firstLine = lines[0].trim();
        if (!firstLine) {
          resolve([]);
          return;
        }
        
        // Simple CSV parsing (handle quoted fields)
        const headers: string[] = [];
        let currentField = '';
        let inQuotes = false;
        
        for (let i = 0; i < firstLine.length; i++) {
          const char = firstLine[i];
          
          if (char === '"') {
            inQuotes = !inQuotes;
          } else if (char === ',' && !inQuotes) {
            headers.push(currentField.trim().replace(/^"|"$/g, ''));
            currentField = '';
          } else {
            currentField += char;
          }
        }
        
        // Add last field
        if (currentField || headers.length > 0) {
          headers.push(currentField.trim().replace(/^"|"$/g, ''));
        }
        
        // Filter out empty headers
        const validHeaders = headers.filter(h => h && h.trim() !== '');
        resolve(validHeaders);
      };
      
      reader.onerror = () => {
        if (encoding === 'UTF-8') {
          // Try GBK if UTF-8 fails
          tryRead('GBK');
        } else {
          reject(new Error('Failed to read file'));
        }
      };
      
      // Read first 10KB to get headers
      if (encoding === 'UTF-8') {
        reader.readAsText(file.slice(0, 10240), 'UTF-8');
      } else {
        // For GBK, we'll need to handle it differently
        // For now, just try UTF-8
        reader.readAsText(file.slice(0, 10240), 'UTF-8');
      }
    };
    
    tryRead();
  });
};

/**
 * Get file type from filename
 */
export const getFileType = (fileName?: string): 'csv' | 'jsonl' | 'xlsx' | 'xls' | 'zip' => {
  const extension = fileName?.split('.').pop()?.toLowerCase() || '';
  if (extension === 'xlsx') {
    return 'xlsx';
  }
  if (extension === 'xls') {
    return 'xls';
  }
  if (extension === 'zip') {
    return 'zip';
  }
  if (extension.includes('jsonl') || extension.includes('json')) {
    return 'jsonl';
  }
  return 'csv';
};

/**
 * Get XLSX headers from file (frontend only)
 */
export const getXlsxHeaders = async (file: File): Promise<string[]> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    
    reader.onload = function (e) {
      try {
        const data = e.target?.result;
        if (!data) {
          reject(new Error('Failed to read file'));
          return;
        }
        
        // Parse workbook
        const workbook = XLSX.read(data, { type: 'binary' });
        
        // Get first sheet
        const firstSheetName = workbook.SheetNames[0];
        if (!firstSheetName) {
          resolve([]);
          return;
        }
        
        const worksheet = workbook.Sheets[firstSheetName];
        
        // Convert to JSON to get headers (first row)
        const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1, defval: '' });
        
        if (jsonData.length === 0) {
          resolve([]);
          return;
        }
        
        // First row is headers
        const headers = (jsonData[0] as any[]).map(h => String(h || '').trim()).filter(h => h);
        resolve(headers);
      } catch (error: any) {
        reject(new Error(`Failed to parse Excel file: ${error.message}`));
      }
    };
    
    reader.onerror = () => {
      reject(new Error('Failed to read file'));
    };
    
    // Read as binary string for xlsx library
    reader.readAsBinaryString(file);
  });
};

/**
 * Get ZIP headers from file (frontend only)
 * Extracts ZIP and reads CSV headers from inside
 */
export const getZipHeaders = async (file: File): Promise<string[]> => {
  try {
    // Load ZIP file
    const zip = await JSZip.loadAsync(file);
    
    // Find CSV file (prefer index.csv, otherwise first .csv file)
    let csvFileName: string | null = null;
    
    // Check for index.csv
    for (const fileName in zip.files) {
      if (fileName === 'index.csv' || fileName.endsWith('/index.csv')) {
        csvFileName = fileName;
        break;
      }
    }
    
    // If not found, find first .csv file
    if (!csvFileName) {
      for (const fileName in zip.files) {
        if (fileName.toLowerCase().endsWith('.csv') && !zip.files[fileName].dir) {
          csvFileName = fileName;
          break;
        }
      }
    }
    
    if (!csvFileName) {
      throw new Error('No CSV file found in ZIP archive');
    }
    
    // Get CSV file content
    const csvFile = zip.files[csvFileName];
    if (!csvFile) {
      throw new Error('CSV file not found in ZIP');
    }
    
    // Read CSV content as text
    const csvContent = await csvFile.async('string');
    
    // Parse first line as headers
    const lines = csvContent.split(/\r?\n/);
    if (lines.length === 0) {
      return [];
    }
    
    const firstLine = lines[0].trim();
    if (!firstLine) {
      return [];
    }
    
    // Simple CSV parsing (handle quoted fields)
    const headers: string[] = [];
    let currentField = '';
    let inQuotes = false;
    
    for (let i = 0; i < firstLine.length; i++) {
      const char = firstLine[i];
      
      if (char === '"') {
        inQuotes = !inQuotes;
      } else if (char === ',' && !inQuotes) {
        headers.push(currentField.trim().replace(/^"|"$/g, ''));
        currentField = '';
      } else {
        currentField += char;
      }
    }
    
    // Add last field
    if (currentField || headers.length > 0) {
      headers.push(currentField.trim().replace(/^"|"$/g, ''));
    }
    
    // Filter out empty headers
    const validHeaders = headers.filter(h => h && h.trim() !== '');
    return validHeaders;
  } catch (error: any) {
    throw new Error(`Failed to read ZIP file: ${error.message}`);
  }
};

/**
 * Get file headers (frontend only)
 */
export const getFileHeaders = async (
  file: File
): Promise<{
  headers: string[];
  error?: string;
}> => {
  try {
    const fileType = getFileType(file.name);
    
    if (fileType === 'csv') {
      const headers = await getCSVHeaders(file);
      return { headers };
    }
    
    if (fileType === 'xlsx' || fileType === 'xls') {
      const headers = await getXlsxHeaders(file);
      return { headers };
    }
    
    if (fileType === 'zip') {
      const headers = await getZipHeaders(file);
      return { headers };
    }
    
    // For JSONL, we can't easily get headers without parsing the whole file
    // Return empty and let user configure manually
    return { headers: [] };
  } catch (error: any) {
    return { headers: [], error: error.message || '文件格式错误' };
  }
};

/**
 * Get default column mapping
 * Based on coze-loop: maps dataset fields (target) to file columns (source)
 */
export const getDefaultColumnMap = (
  fieldSchemas: Array<{ key: string; name: string; description?: string; content_type?: string; default_display_format?: string; is_required?: boolean; status?: string }>,
  csvHeaders: string[]
): Array<{ 
  source: string  // 文件列名（导入数据列）
  target: string  // 数据集字段名（评测集列）
  fieldSchema?: any
}> => {
  return fieldSchemas
    .filter(item => item.name && item.key && item.status !== 'Deleted')
    .map(item => ({
      target: item.key,
      source: csvHeaders.find(
        h => h.toLowerCase() === item.name.toLowerCase() || 
            h.toLowerCase() === item.key.toLowerCase()
      ) || '',
      fieldSchema: item
    }));
};

