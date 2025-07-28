import React, { useState } from 'react';
import { Modal, Upload, Progress, Button, Typography, Space, Alert } from 'antd';
import { InboxOutlined, CheckCircleOutlined } from '@ant-design/icons';
import type { UploadProps } from 'antd';
import useAppStore from '../store/useAppStore';
import { useMultiFileUpload } from '../hooks/useFileUpload';

const { Title, Text } = Typography;
const { Dragger } = Upload;

interface UploadModalProps {
  visible: boolean;
  onClose: () => void;
}

const UploadModal: React.FC<UploadModalProps> = ({ visible, onClose }) => {
  const { setFileTree, setMetadata } = useAppStore();
  const [uploadComplete, setUploadComplete] = useState(false);
  
  const handleUploadSuccess = (file: File) => {
    const files = [file];
    if (files.length > 0) {
      const fileName = file.name.toLowerCase();
      const isText = fileName.endsWith('.txt');
      
      // Create mock file tree and metadata based on file type
      let mockFileTree;
      let mockMetadata;
      
      if (isText) {
        // For TEXT files, create a simple file tree with just the text file
        mockFileTree = [
          {
            name: file.name,
            path: `/${file.name}`,
            type: 'file' as const
          }
        ];
        
        mockMetadata = {
          title: file.name.replace('.txt', ''),
          author: 'Text File Author'
        };
      } else {
        // For EPUB files, create the traditional EPUB structure
        mockFileTree = [
          {
            name: 'META-INF',
            path: '/META-INF',
            type: 'directory' as const,
            children: [
              { name: 'container.xml', path: '/META-INF/container.xml', type: 'file' as const }
            ]
          },
          {
            name: 'OEBPS',
            path: '/OEBPS',
            type: 'directory' as const,
            children: [
              { name: 'content.opf', path: '/OEBPS/content.opf', type: 'file' as const },
              { name: 'toc.ncx', path: '/OEBPS/toc.ncx', type: 'file' as const },
              {
                name: 'Text',
                path: '/OEBPS/Text',
                type: 'directory' as const,
                children: [
                  { name: 'chapter1.xhtml', path: '/OEBPS/Text/chapter1.xhtml', type: 'file' as const },
                  { name: 'chapter2.xhtml', path: '/OEBPS/Text/chapter2.xhtml', type: 'file' as const },
                  { name: 'chapter3.xhtml', path: '/OEBPS/Text/chapter3.xhtml', type: 'file' as const }
                ]
              },
              {
                name: 'Styles',
                path: '/OEBPS/Styles',
                type: 'directory' as const,
                children: [
                  { name: 'stylesheet.css', path: '/OEBPS/Styles/stylesheet.css', type: 'file' as const }
                ]
              },
              {
                name: 'Images',
                path: '/OEBPS/Images',
                type: 'directory' as const,
                children: [
                  { name: 'cover.jpg', path: '/OEBPS/Images/cover.jpg', type: 'file' as const }
                ]
              }
            ]
          }
        ];
        
        mockMetadata = {
          title: file.name.replace('.epub', ''),
          author: 'Sample Author'
        };
      }
      
      setFileTree(mockFileTree);
      setMetadata(mockMetadata);
      setUploadComplete(true);
      
      setTimeout(() => {
        handleClose();
      }, 1500);
    }
  };
  
  const handleUploadError = (error: string) => {
    Modal.error({
      title: 'Upload Error',
      content: error,
    });
  };
  
  const { uploadState, uploadFiles, resetUpload, isDragOver, dragHandlers } = useMultiFileUpload(
    handleUploadSuccess,
    handleUploadError
  );

  const uploadProps: UploadProps = {
    name: 'file',
    multiple: false,
    accept: '.epub,.txt',
    showUploadList: false,
    beforeUpload: (file) => {
      uploadFiles([file]);
      return false; // Prevent default upload
    },
  };
  
  const handleClose = () => {
    resetUpload();
    setUploadComplete(false);
    onClose();
  };

  return (
    <Modal
      title="Upload File"
      open={visible}
      onCancel={handleClose}
      footer={null}
      width={500}
      destroyOnHidden
    >
      <div className="py-4">
        {!uploadState.isUploading && !uploadComplete && (
          <>
            <div className="text-center mb-6">
              <Text className="text-gray-600">
                Select an EPUB or TEXT file to start editing
              </Text>
            </div>
            
            <Dragger {...uploadProps} className="mb-4">
              <p className="ant-upload-drag-icon">
                <InboxOutlined />
              </p>
              <p className="ant-upload-text">Click or drag EPUB or TEXT file to this area to upload</p>
              <p className="ant-upload-hint">
                Support for single EPUB (.epub) or TEXT (.txt) file upload. File size should be less than 100MB.
              </p>
            </Dragger>
          </>
        )}

        {uploadState.isUploading && (
          <div className="text-center py-8">
            <Progress 
              type="circle" 
              percent={uploadState.progress} 
              size={100}
              className="mb-4"
            />
            <div>
              <Text className="text-lg">Processing file...</Text>
              <br />
              <Text type="secondary">Analyzing content</Text>
            </div>
          </div>
        )}

        {uploadComplete && (
          <div className="text-center py-8">
            <CheckCircleOutlined className="text-green-500 text-5xl mb-4" />
            <Alert
              message="Upload Successful!"
              description="Your file has been processed and is ready for editing."
              type="success"
              showIcon
              className="mb-4"
            />
            <Text type="secondary">Redirecting to editor...</Text>
          </div>
        )}

        {!uploadState.isUploading && !uploadComplete && (
          <div className="text-center mt-4">
            <Text type="secondary" className="text-xs">
              Supported formats: .epub, .txt • Maximum size: 100MB
            </Text>
          </div>
        )}
      </div>
    </Modal>
  );
};

export default UploadModal;