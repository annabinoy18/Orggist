import React, { useState, useRef, useEffect } from 'react';
import './UploadPage.css';
import TopBar from './TopBar';
import { toast, ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

const UploadPage = () => {
  const [files, setFiles] = useState([]);
  const [codeContent, setCodeContent] = useState('');
  const fileInputRef = useRef(null);

  useEffect(() => {
    const intervals = [];

    files.forEach((file, index) => {
      if (file.status === 'uploading' && file.progress < 100) {
        const interval = setInterval(() => {
          setFiles(prevFiles => {
            const updatedFiles = [...prevFiles];
            const current = updatedFiles[index];

            if (current.progress < 100) {
              current.progress += Math.floor(Math.random() * 10 + 5);
              if (current.progress >= 100) {
                current.progress = 100;
                current.status = 'completed';
                current.speed = '';
                clearInterval(interval);
              }
            }

            return updatedFiles;
          });
        }, 500);

        intervals.push(interval);
      }
    });

    return () => intervals.forEach(clearInterval);
  }, [files]);

  const handleRemoveFile = (indexToRemove) => {
    const updatedFiles = files.filter((_, index) => index !== indexToRemove);
    setFiles(updatedFiles);

    if (updatedFiles.length === 0 && fileInputRef.current) {
      fileInputRef.current.value = null;  // ✅ Correct line
    }
  };



  const handleFileChange = (e) => {
    const selectedFiles = Array.from(e.target.files);
    const acceptedTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
    const MAX_FILE_SIZE_MB = 50;

    const newFiles = selectedFiles.map(file => {
      const fileSizeMB = file.size / (1024 * 1024);
      const isValidType = acceptedTypes.includes(file.type);
      const isValidSize = fileSizeMB <= MAX_FILE_SIZE_MB;
      
      return {
        file,
        name: file.name,
        size: `${fileSizeMB.toFixed(1)} mb`,
        progress: 0,
        speed: '100KB/sec',
        status: 'pending',
        isValid: isValidType && isValidSize,
        error: !isValidType ? 'Unsupported file type' : !isValidSize ? `File too large (max ${MAX_FILE_SIZE_MB}MB)` : null
      };
    });

    // Show error messages for invalid files
    newFiles.forEach(file => {
      if (!file.isValid) {
        toast.error(`❌ ${file.name}: ${file.error}`);
      }
    });

    setFiles(prev => [...prev, ...newFiles]);
  };

  const handleFileUpload = async () => {
    if (!fileInputRef.current || !fileInputRef.current.files.length) {
      toast.error("❌ No files selected.");
      return false;
    }

    const files = fileInputRef.current.files;
    const formData = new FormData();
    let hasValidFiles = false;

    // Only add valid files to formData
    for (let file of files) {
      const fileSizeMB = file.size / (1024 * 1024);
      if (fileSizeMB <= 50) {  // MAX_FILE_SIZE_MB
        formData.append("files", file);
        hasValidFiles = true;
      }
    }

    if (!hasValidFiles) {
      toast.error("❌ No valid files to upload.");
      return false;
    }

    try {
      // First upload to S3
      const res = await fetch("http://localhost:8080/upload", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        if (res.status === 413) {
          toast.error("❌ File upload failed: file size too large for server.");
        } else {
          toast.error("❌ File upload failed.");
        }
        // Update status for uploading files to failed
        setFiles(prevFiles => 
          prevFiles.map(f => 
            f.status === 'uploading' ? { ...f, status: 'failed', error: 'Upload failed' } : f
          )
        );
        return false;
      }

      // Get presigned URLs from the response
      const presignedUrls = await res.json();

      // Send URLs to PDF processor
      try {
        const pdfProcessorRes = await fetch("http://localhost:8001/process-pdfs", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            presigned_urls: presignedUrls,
            file_names: Array.from(files).map(f => f.name)
          })
        });

        if (!pdfProcessorRes.ok) {
          console.error("PDF processing failed:", await pdfProcessorRes.text());
          toast.warning("⚠️ Files uploaded but PDF processing failed. You may not be able to search through these files.");
        } else {
          toast.success("✅ Files uploaded and processed successfully!");
        }
      } catch (pdfError) {
        console.error("Error sending to PDF processor:", pdfError);
        toast.warning("⚠️ Files uploaded but PDF processing failed. You may not be able to search through these files.");
      }

      // Update status for valid files to completed
      setFiles(prevFiles => 
        prevFiles.map(f => 
          f.isValid && f.status === 'uploading' ? { ...f, status: 'completed' } : f
        )
      );

      fileInputRef.current.value = null;
      return true;
    } catch (error) {
      toast.error("❌ Error uploading files: " + error.message);
      // Update status for uploading files to failed
      setFiles(prevFiles => 
        prevFiles.map(f => 
          f.status === 'uploading' ? { ...f, status: 'failed', error: 'Upload failed' } : f
        )
      );
      return false;
    }
  };

  const handleCodeContentUpload = async () => {
    if (!codeContent.trim()) {
      toast.warning("⚠️ Text content is empty. Skipped text upload.");
      return false;
    }

    try {
      toast.info("⏳ Uploading text content...");

      // Store in both PostgreSQL and vector DB through Spring Boot
      const response = await fetch("http://localhost:8080/code-upload", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          content: codeContent,
          username: "Test User" // You can modify this to use actual username
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        toast.error("❌ Failed to upload text: " + errorText);
        return false;
      }

      toast.success("✅ Text uploaded successfully to both databases.");
      return true;
    } catch (err) {
      console.error("Upload error:", err);
      toast.error("❌ Network or server error.");
      return false;
    }
  };


  const handleUpload = async () => {
    const hasFiles = fileInputRef.current && fileInputRef.current.files.length > 0;
    const hasCode = codeContent.trim().length > 0;

    if (hasFiles && hasCode) {
      toast.error("❌ You can only upload either files or text, not both.");
      return;
    }

    if (!hasFiles && !hasCode) {
      toast.error("❌ Please add a file or enter some text.");
      return;
    }

    if (hasFiles) {
      // Check if there are any files in the files state that are still uploading
      const hasUploadingFiles = files.some(file => file.status === 'uploading');
      if (hasUploadingFiles) {
        toast.info("⏳ Files are still uploading. Please wait.");
        return;
      }

      // Check if there are any pending files to upload
      const hasPendingFiles = files.some(file => file.status === 'pending');
      if (!hasPendingFiles) {
        toast.info("ℹ️ Please add new files to upload.");
        return;
      }

      // Update status to uploading for pending files
      setFiles(prevFiles => 
        prevFiles.map(file => 
          file.status === 'pending' ? { ...file, status: 'uploading' } : file
        )
      );

      await handleFileUpload();
    } else if (hasCode) {
      await handleCodeContentUpload();
    }
  };

  return (
    <div className="upload-container">
      <ToastContainer
        position="top-right"
        autoClose={3000}
        hideProgressBar={false}
        newestOnTop
        closeOnClick
        rtl={false}
        pauseOnFocusLoss
        draggable
        pauseOnHover
        theme="light"
      />
      <TopBar user={{ name: "Test User", picture: "https://via.placeholder.com/40" }} />

      <div className="header">
        <h2>Upload Files & Texts</h2>
      </div>

      <div className="upload-card">
        <textarea
          className="code-input"
          placeholder="Paste your text here..."
          value={codeContent}
          onChange={(e) => setCodeContent(e.target.value)}
        ></textarea>

        <div className="upload-flex-box">
          <div className="upload-box">
            <div className="upload-placeholder">
              <img src="https://img.icons8.com/clouds/100/upload.png" alt="Upload" />
              <p>
                Drop your files here.{" "}
                <span
                  className="browse"
                  onClick={() => fileInputRef.current && fileInputRef.current.click()}
                >
                  or Browse
                </span>
              </p>
              <input
                type="file"
                accept=".pdf,.docx"
                multiple
                ref={fileInputRef}
                style={{ display: "none" }}
                onChange={handleFileChange}
              />
            </div>
          </div>

          <div className="file-list">
            {files.map((file, index) => (
              <div key={index} className={`file-item ${!file.isValid ? 'file-invalid' : ''}`}>
                <div className="file-info">
                  <img
                    src={
                      file.name.endsWith('.png')
                        ? 'https://img.icons8.com/ios-filled/20/image.png'
                        : file.name.endsWith('.pdf')
                        ? 'https://img.icons8.com/ios-filled/20/pdf.png'
                        : 'https://img.icons8.com/ios-filled/20/document.png'
                    }
                    alt="icon"
                  />
                  <span>{file.name}</span>
                  <span className="file-size">{file.size}</span>

                  <span className="file-remove" onClick={() => handleRemoveFile(index)}>×</span>
                </div>
                {!file.isValid ? (
                  <div className="file-status-error">{file.error}</div>
                ) : file.status === 'completed' ? (
                  <div className="file-status-complete">Completed</div>
                ) : file.status === 'failed' ? (
                  <div className="file-status-error">{file.error}</div>
                ) : (
                  <div className="progress-section">
                    <div className="progress-bar">
                      <div
                        className="progress-fill"
                        style={{ width: `${file.progress}%` }}
                      ></div>
                    </div>
                    <span className="progress-text">
                      {file.progress}% done &nbsp; {file.speed}
                    </span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="upload-button-container">
          <button className="upload-btn" onClick={handleUpload}>
            Upload 
          </button>
        </div>
      </div>
    </div>
  );
};

export default UploadPage;
