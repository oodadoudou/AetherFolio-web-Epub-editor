import React, { useState } from 'react';
import { Modal, Upload, Progress, Button, Typography, Space, Alert, App } from 'antd';
import { InboxOutlined, CheckCircleOutlined } from '@ant-design/icons';
import type { UploadProps } from 'antd';
import useAppStore from '../store/useAppStore';
import { useMultiFileUpload } from '../hooks/useFileUpload';
import { uploadService } from '../services/upload';
import { sessionService } from '../services/session';
import { useNavigate } from 'react-router-dom';

const { Title, Text } = Typography;
const { Dragger } = Upload;

interface UploadModalProps {
  visible: boolean;
  onClose: () => void;
}

const UploadModal: React.FC<UploadModalProps> = ({ visible, onClose }) => {
  const { modal } = App.useApp();
  const { setFileTree, setMetadata } = useAppStore();
  const [uploadComplete, setUploadComplete] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const navigate = useNavigate();
  
  const handleUploadSuccess = async (file: File) => {
    try {
      console.log('Starting file upload:', file.name);
      
      // 首先验证文件
      const validation = await uploadService.validateFile(file);
      if (!validation.isValid) {
        throw new Error(validation.errors.join(', '));
      }
      
      // 显示警告信息（如果有）
      if (validation.warnings.length > 0) {
        modal.warning({
          title: '文件警告',
          content: validation.warnings.join(', '),
          okText: '继续上传',
        });
      }
      
      // 根据文件类型选择上传方法
      let uploadResponse;
      const fileExtension = file.name.toLowerCase().split('.').pop();
      if (fileExtension === 'epub') {
        uploadResponse = await uploadService.uploadEpub(file, {
          validate_structure: true,
          extract_metadata: true
        });
      } else if (fileExtension === 'txt') {
        uploadResponse = await uploadService.uploadText(file, {
          encoding: 'utf-8'
        });
      } else {
        throw new Error('不支持的文件类型');
      }
      
      console.log('Upload successful:', uploadResponse);
      
      // 更新应用状态
      setFileTree(uploadResponse.file_tree || []);
      setMetadata(uploadResponse.metadata || {});
      setSessionId(uploadResponse.session_id);
      setUploadComplete(true);
      
      // 保存会话ID到 localStorage，用于浏览器关闭时清理
      localStorage.setItem('currentSessionId', uploadResponse.session_id);
      
      // 延迟跳转到编辑器
      setTimeout(() => {
        navigate(`/editor/${uploadResponse.session_id}`);
        handleClose();
      }, 1500);
      
    } catch (error) {
      console.error('Upload error:', error);
      let errorMessage = 'Upload failed';
      
      // 处理不同类型的错误
      if (error instanceof Error) {
        errorMessage = error.message;
      } else if (typeof error === 'object' && error !== null) {
        // 处理API错误响应
        const apiError = error as any;
        if (apiError.response?.data?.message) {
          errorMessage = apiError.response.data.message;
        } else if (apiError.message) {
          errorMessage = apiError.message;
        } else if (apiError.detail) {
          errorMessage = apiError.detail;
        }
      }
      
      handleUploadError(errorMessage);
    }
  };
  
  const handleUploadError = (error: string) => {
    console.error('Upload error details:', error);
    
    // 解析错误信息，提供更友好的提示
    let errorMessage = error;
    let errorTitle = '上传失败';
    
    if (error.includes('文件大小超出限制')) {
      errorTitle = '文件过大';
      errorMessage = '文件大小超出限制。EPUB文件最大100MB，TXT文件最大10MB。';
    } else if (error.includes('不支持的文件格式') || error.includes('文件格式')) {
      errorTitle = '文件格式错误';
      errorMessage = '仅支持 .epub 和 .txt 文件格式。';
    } else if (error.includes('网络') || error.includes('Failed to fetch')) {
      errorTitle = '网络错误';
      errorMessage = '网络连接失败，请检查网络连接后重试。';
    } else if (error.includes('无效的EPUB文件')) {
      errorTitle = 'EPUB文件错误';
      errorMessage = 'EPUB文件格式无效或已损坏，请选择有效的EPUB文件。';
    } else if (error.includes('无效的文本文件')) {
      errorTitle = '文本文件错误';
      errorMessage = '文本文件格式无效，请确保文件为有效的UTF-8或GBK编码文本。';
    }
    
    modal.error({
      title: errorTitle,
      content: errorMessage,
      okText: '确定',
    });
  };
  
  const { uploadState, uploadFiles, resetUpload } = useMultiFileUpload(
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
              description={`Your file has been processed and is ready for editing. Session ID: ${sessionId}`}
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