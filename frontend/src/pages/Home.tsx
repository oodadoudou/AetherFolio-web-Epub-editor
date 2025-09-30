import React from 'react';
import { ConfigProvider, Button, FloatButton, App } from 'antd';
import { PlusOutlined, EditOutlined, MergeOutlined, SwapOutlined, QuestionCircleOutlined } from '@ant-design/icons';

import UploadModal from '../components/UploadModal';
import UserMenu from '../components/UserMenu';
import useAppStore from '../store/useAppStore';

interface HomeProps {
  isDarkMode: boolean;
  traeDarkTheme: unknown;
  traeLightTheme: unknown;
}

const Home: React.FC<HomeProps> = ({ isDarkMode, traeDarkTheme, traeLightTheme }) => {
  const { message } = App.useApp();
  const {
    isUploadModalVisible,
    setUploadModalVisible,
  } = useAppStore();

  const [helpTooltipVisible, setHelpTooltipVisible] = React.useState(false);

  const handleOpenUpload = () => {
    setUploadModalVisible(true);
  };

  const handleMergeClick = () => {
    message.info({
      content: '暂不支持，请等待更新 ✨',
      duration: 3,
    });
  };

  const handleConvertClick = () => {
    message.info({
      content: '暂不支持，请等待更新 ✨',
      duration: 3,
    });
  };

  const handleHelpClick = () => {
    setHelpTooltipVisible(true);
  };

  const handleCloseTooltip = () => {
    setHelpTooltipVisible(false);
  };

  return (
    <ConfigProvider theme={isDarkMode ? traeDarkTheme : traeLightTheme}>
      <div className={`h-screen flex flex-col ${isDarkMode ? 'bg-neutral-900' : 'bg-slate-50'}`} style={isDarkMode ? {backgroundColor: '#1a1a1a'} : {}}>
        {/* Top Navigation */}
        <div className={`${isDarkMode ? 'bg-neutral-800 border-neutral-700' : 'bg-white border-gray-200'} border-b px-6 py-4`}>
          <div className="flex justify-between items-center">
            <div className="flex items-center space-x-4">
              <h1 className={`text-xl font-bold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
                AetherFolio
              </h1>
            </div>
            <UserMenu />
          </div>
        </div>
        
        {/* Main Content Area */}
        <div className="flex-1 overflow-hidden">
          {/* Main Interface */}
          <div className={`h-full flex items-center justify-center ${isDarkMode ? 'bg-neutral-900' : 'bg-white'}`} style={isDarkMode ? {backgroundColor: '#1a1a1a'} : {}}>
            <div className="text-center space-y-8">
              <div className="text-6xl text-slate-300 mb-4">📚</div>
              <h1 className={`text-4xl font-bold ${isDarkMode ? 'text-neutral-100' : 'text-slate-800'}`} style={isDarkMode ? {color: '#e5e5e5'} : {}}>AetherFolio</h1>
              <p className={`text-lg ${isDarkMode ? 'text-neutral-400' : 'text-slate-600'} max-w-lg`} style={isDarkMode ? {color: '#a3a3a3'} : {}}>
                A modern EPUB editor with powerful editing, merging, and conversion capabilities.
              </p>
              
              {/* Main Action Buttons */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-12">
                {/* Edit EPUB */}
                <div className={`p-6 rounded-lg border-2 border-dashed transition-all hover:border-solid cursor-pointer ${isDarkMode ? 'border-neutral-600 hover:border-green-500 bg-neutral-700 hover:bg-neutral-600' : 'border-slate-300 hover:border-green-500 bg-slate-50 hover:bg-slate-100'}`} onClick={handleOpenUpload}>
                  <div className="text-center space-y-4">
                    <EditOutlined className={`text-4xl ${isDarkMode ? 'text-green-400' : 'text-green-600'}`} />
                    <h3 className={`text-xl font-semibold ${isDarkMode ? 'text-neutral-100' : 'text-slate-800'}`}>Edit EPUB</h3>
                    <p className={`text-sm ${isDarkMode ? 'text-neutral-400' : 'text-slate-600'}`}>
                      Upload and edit EPUB files with advanced text processing capabilities
                    </p>
                  </div>
                </div>
                
                {/* Merge EPUBs */}
                <div 
                  className={`p-6 rounded-lg border-2 border-dashed transition-all hover:border-solid cursor-pointer opacity-60 ${isDarkMode ? 'border-neutral-600 hover:border-gray-500 bg-neutral-700 hover:bg-neutral-600' : 'border-slate-300 hover:border-gray-400 bg-slate-50 hover:bg-slate-100'}`}
                  onClick={handleMergeClick}
                >
                  <div className="text-center space-y-4">
                    <MergeOutlined className={`text-4xl ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`} />
                    <h3 className={`text-xl font-semibold ${isDarkMode ? 'text-neutral-300' : 'text-slate-600'}`}>Merge Files</h3>
                    <p className={`text-sm ${isDarkMode ? 'text-neutral-500' : 'text-slate-500'}`}>
                      Combine multiple files into a single publication
                    </p>
                  </div>
                </div>
                
                {/* Convert Files */}
                <div 
                  className={`p-6 rounded-lg border-2 border-dashed transition-all hover:border-solid cursor-pointer opacity-60 ${isDarkMode ? 'border-neutral-600 hover:border-gray-500 bg-neutral-700 hover:bg-neutral-600' : 'border-slate-300 hover:border-gray-400 bg-slate-50 hover:bg-slate-100'}`}
                  onClick={handleConvertClick}
                >
                  <div className="text-center space-y-4">
                    <SwapOutlined className={`text-4xl ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`} />
                    <h3 className={`text-xl font-semibold ${isDarkMode ? 'text-neutral-300' : 'text-slate-600'}`}>Convert Files</h3>
                    <p className={`text-sm ${isDarkMode ? 'text-neutral-500' : 'text-slate-500'}`}>
                      Convert between different e-book formats and document types
                    </p>
                  </div>
                </div>
              </div>
              
              {/* Help Button */}
              <Button 
                className="fixed top-6 right-6 w-14 h-14 rounded-full flex items-center justify-center shadow-lg hover:scale-110 transition-all z-50"
                style={{
                  backgroundColor: '#22c55e',
                  borderColor: '#22c55e',
                  color: 'white'
                }}
                onClick={handleHelpClick}
                icon={<QuestionCircleOutlined style={{ fontSize: '24px' }} />}
                title="Help"
              />
              
              {/* Help Tooltip */}
              {helpTooltipVisible && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={handleCloseTooltip}>
                  <div 
                    className={`${isDarkMode ? 'bg-neutral-800 border-neutral-600' : 'bg-white border-gray-200'} rounded-lg p-6 max-w-sm mx-4 text-center shadow-xl border`} 
                    onClick={(e) => e.stopPropagation()}
                    style={isDarkMode ? {backgroundColor: '#2d2d2d', borderColor: '#404040'} : {}}
                  >
                    <div className="text-4xl mb-4 text-yellow-500">
                      <QuestionCircleOutlined />
                    </div>
                    <h3 className={`text-xl font-bold mb-2 ${isDarkMode ? 'text-white' : 'text-gray-800'}`} style={isDarkMode ? {color: '#e5e5e5'} : {}}>帮助</h3>
                    <p className={`${isDarkMode ? 'text-neutral-300' : 'text-gray-600'} mb-6`} style={isDarkMode ? {color: '#a3a3a3'} : {}}>
                      当前只有 Edit 功能可用，Merge 和 Convert 功能正在开发中。
                    </p>
                    <Button 
                      type="primary" 
                      onClick={handleCloseTooltip}
                      className="px-6"
                      style={{
                        backgroundColor: '#22c55e',
                        borderColor: '#22c55e',
                        color: 'white'
                      }}
                    >
                      知道了
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
        
        {/* Floating Action Button */}
        <FloatButton 
          icon={<PlusOutlined />}
          type="primary"
          style={{ right: 24, bottom: 24 }}
          onClick={handleOpenUpload}
          tooltip="Upload EPUB File"
        />
        
        {/* Modals */}
        <UploadModal 
          visible={isUploadModalVisible}
          onClose={() => setUploadModalVisible(false)}
        />
      </div>
    </ConfigProvider>
  );
};

export default Home;