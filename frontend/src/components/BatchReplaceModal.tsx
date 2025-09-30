import React, { useState } from 'react';
import { 
  Modal, 
  Upload, 
  Button, 
  Progress, 
  Table, 
  Typography, 
  Space, 
  Alert,
  Divider,
  Card
} from 'antd';
import { 
  UploadOutlined, 
  DownloadOutlined, 
  PlayCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined
} from '@ant-design/icons';
import type { UploadFile, UploadProps } from 'antd';

const { Title, Text } = Typography;

interface ReplaceRule {
  id: string;
  find: string;
  replace: string;
  scope: string;
  status: 'pending' | 'processing' | 'completed' | 'error';
  matches: number;
}

interface BatchReplaceModalProps {
  visible: boolean;
  onClose: () => void;
  isDarkMode?: boolean;
}

const BatchReplaceModal: React.FC<BatchReplaceModalProps> = ({ visible, onClose, isDarkMode = false }) => {
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [rules, setRules] = useState<ReplaceRule[]>([]);
  const [currentStep, setCurrentStep] = useState<'upload' | 'processing' | 'completed'>('upload');

  const uploadProps: UploadProps = {
    name: 'file',
    multiple: false,
    accept: '.csv,.xlsx,.json',
    fileList,
    beforeUpload: (file) => {
      setFileList([file]);
      // Mock parsing rules from file
      const mockRules: ReplaceRule[] = [
        {
          id: '1',
          find: 'old text 1',
          replace: 'new text 1',
          scope: 'All files',
          status: 'pending',
          matches: 0
        },
        {
          id: '2',
          find: 'old text 2',
          replace: 'new text 2',
          scope: 'HTML files only',
          status: 'pending',
          matches: 0
        },
        {
          id: '3',
          find: 'sample text',
          replace: 'updated text',
          scope: 'TEXT files only',
          status: 'pending',
          matches: 0
        }
      ];
      setRules(mockRules);
      return false; // Prevent auto upload
    },
    onRemove: () => {
      setFileList([]);
      setRules([]);
    }
  };

  const handleDownloadTemplate = () => {
    // Mock template download
    const csvContent = 'find,replace,scope\n"old text","new text","all"\n"example","sample","html"\n"sample text","updated text","txt"';
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'batch_replace_template.csv';
    a.click();
    window.URL.revokeObjectURL(url);
  };

  const handleStartReplace = () => {
    setIsProcessing(true);
    setCurrentStep('processing');
    setProgress(0);

    // Mock processing
    const interval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 100) {
          clearInterval(interval);
          setIsProcessing(false);
          setCurrentStep('completed');
          // Update rules status
          setRules(prev => prev.map(rule => ({
            ...rule,
            status: 'completed',
            matches: Math.floor(Math.random() * 10) + 1
          })));
          return 100;
        }
        return prev + 10;
      });
    }, 300);
  };

  const handleReset = () => {
    setFileList([]);
    setRules([]);
    setProgress(0);
    setCurrentStep('upload');
    setIsProcessing(false);
  };

  const columns = [
    {
      title: 'Find',
      dataIndex: 'find',
      key: 'find',
      width: '30%',
      render: (text: string) => <Text code>{text}</Text>
    },
    {
      title: 'Replace',
      dataIndex: 'replace',
      key: 'replace',
      width: '30%',
      render: (text: string) => <Text code>{text}</Text>
    },
    {
      title: 'Scope',
      dataIndex: 'scope',
      key: 'scope',
      width: '20%'
    },
    {
      title: 'Matches',
      dataIndex: 'matches',
      key: 'matches',
      width: '10%',
      render: (matches: number) => matches > 0 ? matches : '-'
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: '10%',
      render: (status: string) => {
        const statusConfig = {
          pending: { icon: <ExclamationCircleOutlined />, color: 'orange' },
          processing: { icon: <PlayCircleOutlined />, color: 'blue' },
          completed: { icon: <CheckCircleOutlined />, color: 'green' },
          error: { icon: <ExclamationCircleOutlined />, color: 'red' }
        };
        const config = statusConfig[status as keyof typeof statusConfig];
        return (
          <Space>
            <span style={{ color: config.color }}>{config.icon}</span>
            <span>{status}</span>
          </Space>
        );
      }
    }
  ];

  // Theme styles
  const modalClassName = isDarkMode ? 'dark-modal' : 'light-modal';
  const cardStyle = isDarkMode ? {
    backgroundColor: '#1f1f1f',
    borderColor: '#333',
    color: '#e5e5e5'
  } : {};
  const alertStyle = isDarkMode ? {
    backgroundColor: '#2d2d2d',
    borderColor: '#404040',
    color: '#e5e5e5'
  } : {};
  const tableStyle = isDarkMode ? {
    backgroundColor: '#1f1f1f',
    color: '#e5e5e5'
  } : {};

  return (
    <Modal
      title="Batch Replace"
      open={visible}
      onCancel={onClose}
      width={800}
      footer={null}
      destroyOnHidden
      className={modalClassName}
    >
      <div className="space-y-4">
        {currentStep === 'upload' && (
          <>
            <Alert
              message="Upload a CSV/Excel file with replacement rules"
              description="The file should contain columns: find, replace, scope"
              type="info"
              showIcon
              style={alertStyle}
            />
            
            <Card style={cardStyle}>
              <Space direction="vertical" className="w-full">
                <div className="flex justify-between items-center">
                  <Title level={5}>Step 1: Upload Rules File</Title>
                  <Button 
                    icon={<DownloadOutlined />} 
                    onClick={handleDownloadTemplate}
                  >
                    Download Template
                  </Button>
                </div>
                
                <Upload.Dragger {...uploadProps}>
                  <p className="ant-upload-drag-icon">
                    <UploadOutlined />
                  </p>
                  <p className="ant-upload-text">Click or drag file to this area to upload</p>
                  <p className="ant-upload-hint">
                    Support CSV, Excel, or JSON format
                  </p>
                </Upload.Dragger>
              </Space>
            </Card>

            {rules.length > 0 && (
              <Card style={cardStyle}>
                <Title level={5}>Step 2: Review Rules</Title>
                <Table 
                  dataSource={rules} 
                  columns={columns} 
                  pagination={false}
                  size="small"
                  rowKey="id"
                  style={tableStyle}
                />
                <Divider />
                <div className="text-center">
                  <Button 
                    type="primary" 
                    icon={<PlayCircleOutlined />}
                    onClick={handleStartReplace}
                    size="large"
                  >
                    Start Batch Replace
                  </Button>
                </div>
              </Card>
            )}
          </>
        )}

        {currentStep === 'processing' && (
          <Card style={cardStyle}>
            <div className="text-center space-y-4">
              <Title level={4}>Processing Replacements...</Title>
              <Progress 
                type="circle" 
                percent={progress} 
                size={120}
                status={isProcessing ? 'active' : 'success'}
              />
              <div>
                <Text>Applying replacement rules to files...</Text>
              </div>
            </div>
          </Card>
        )}

        {currentStep === 'completed' && (
          <>
            <Alert
              message="Batch replacement completed successfully!"
              description="All replacement rules have been applied to the selected files."
              type="success"
              showIcon
              style={alertStyle}
            />
            
            <Card style={cardStyle}>
              <Title level={5}>Results Summary</Title>
              <Table 
                dataSource={rules} 
                columns={columns} 
                pagination={false}
                size="small"
                rowKey="id"
                style={tableStyle}
              />
              <Divider />
              <div className="text-center space-x-2">
                <Button onClick={handleReset}>
                  New Replacement
                </Button>
                <Button type="primary" onClick={onClose}>
                  Close
                </Button>
              </div>
            </Card>
          </>
        )}
      </div>
    </Modal>
  );
};

export default BatchReplaceModal;