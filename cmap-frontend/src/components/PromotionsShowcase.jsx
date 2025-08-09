import React, { useState, useRef, useEffect } from 'react';
import { Upload, Trash2, ChevronLeft, ChevronRight, Play, Pause, FileImage, Eye } from 'lucide-react';

const PromotionsShowcase = () => {
  const [promotions, setPromotions] = useState([]);
  const [currentSlide, setCurrentSlide] = useState(0);
  const [isAutoPlay, setIsAutoPlay] = useState(true);
  const [dragOver, setDragOver] = useState(false);
  const [viewMode, setViewMode] = useState('showcase'); // 'showcase' or 'manage'
  const fileInputRef = useRef(null);
  const autoPlayRef = useRef(null);

  // 自动播放功能
  useEffect(() => {
    if (isAutoPlay && promotions.length > 1) {
      autoPlayRef.current = setInterval(() => {
        setCurrentSlide(prev => (prev + 1) % promotions.length);
      }, 5000); // 5秒切换一次
    } else {
      clearInterval(autoPlayRef.current);
    }

    return () => clearInterval(autoPlayRef.current);
  }, [isAutoPlay, promotions.length]);

  // 重置当前幻灯片
  useEffect(() => {
    if (currentSlide >= promotions.length && promotions.length > 0) {
      setCurrentSlide(0);
    }
  }, [promotions.length, currentSlide]);

  // 处理文件上传
  const handleFileUpload = (files) => {
    Array.from(files).forEach(file => {
      // 检查文件类型
      const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
      if (!allowedTypes.includes(file.type)) {
        alert(`文件 ${file.name} 不是支持的图片格式。请上传 JPG, PNG, GIF, 或 WebP 格式的图片。`);
        return;
      }

      // 检查文件大小 (最大10MB)
      if (file.size > 10 * 1024 * 1024) {
        alert(`文件 ${file.name} 太大。请上传小于10MB的图片。`);
        return;
      }

      // 读取文件并转换为base64
      const reader = new FileReader();
      reader.onload = (e) => {
        const newPromotion = {
          id: Date.now() + Math.random(),
          name: file.name.replace(/\.[^/.]+$/, ""), // 移除文件扩展名
          image: e.target.result,
          size: file.size,
          uploadDate: new Date().toISOString(),
          type: file.type
        };

        setPromotions(prev => [...prev, newPromotion]);
        
        // 如果是第一个上传的文件，设置为当前幻灯片
        if (promotions.length === 0) {
          setCurrentSlide(0);
        }
      };
      reader.readAsDataURL(file);
    });
  };

  // 拖拽处理
  const handleDragOver = (e) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const files = Array.from(e.dataTransfer.files);
    handleFileUpload(files);
  };

  // 删除推广海报
  const deletePromotion = (id) => {
    if (window.confirm('确定要删除这个海报吗？')) {
      setPromotions(prev => prev.filter(promo => promo.id !== id));
    }
  };

  // 幻灯片导航
  const goToSlide = (index) => {
    setCurrentSlide(index);
  };

  const nextSlide = () => {
    setCurrentSlide(prev => (prev + 1) % promotions.length);
  };

  const prevSlide = () => {
    setCurrentSlide(prev => (prev - 1 + promotions.length) % promotions.length);
  };

  // 切换自动播放
  const toggleAutoPlay = () => {
    setIsAutoPlay(!isAutoPlay);
  };

  // 全屏查看
  const viewFullscreen = (promotion) => {
    const newWindow = window.open();
    newWindow.document.write(`
      <html>
        <head>
          <title>${promotion.name}</title>
          <style>
            body { margin: 0; padding: 20px; background: #000; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
            img { max-width: 100%; max-height: 100%; object-fit: contain; }
          </style>
        </head>
        <body>
          <img src="${promotion.image}" alt="${promotion.name}" />
        </body>
      </html>
    `);
  };

  // 展示模式渲染
  const renderShowcaseMode = () => {
    if (promotions.length === 0) {
      return (
        <div className="h-full flex items-center justify-center">
          <div className="text-center">
            <FileImage className="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-700 mb-2">No Promotions Available</h3>
            <p className="text-gray-500">Upload some promotional materials to get started</p>
            <button
              onClick={() => setViewMode('manage')}
              className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
            >
              Upload Promotions
            </button>
          </div>
        </div>
      );
    }

    const currentPromotion = promotions[currentSlide];

    return (
      <div className="h-full flex flex-col">
        {/* 展示区域 */}
        <div className="flex-1 relative bg-black rounded-lg overflow-hidden">
          <img
            src={currentPromotion.image}
            alt={currentPromotion.name}
            className="w-full h-full object-contain"
          />
          
          {/* 导航按钮 */}
          {promotions.length > 1 && (
            <>
              <button
                onClick={prevSlide}
                className="absolute left-4 top-1/2 transform -translate-y-1/2 bg-black bg-opacity-50 text-white p-2 rounded-full hover:bg-opacity-75 transition-opacity"
              >
                <ChevronLeft className="w-6 h-6" />
              </button>
              <button
                onClick={nextSlide}
                className="absolute right-4 top-1/2 transform -translate-y-1/2 bg-black bg-opacity-50 text-white p-2 rounded-full hover:bg-opacity-75 transition-opacity"
              >
                <ChevronRight className="w-6 h-6" />
              </button>
            </>
          )}

          {/* 信息覆盖层 */}
          <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black to-transparent p-6">
            <h3 className="text-white text-xl font-semibold mb-2">{currentPromotion.name}</h3>
            <div className="flex items-center justify-between">
              <p className="text-gray-300 text-sm">
                Uploaded {new Date(currentPromotion.uploadDate).toLocaleDateString()}
              </p>
              <div className="flex space-x-2">
                <button
                  onClick={() => viewFullscreen(currentPromotion)}
                  className="text-white hover:text-gray-300 transition-colors"
                  title="View Fullscreen"
                >
                  <Eye className="w-5 h-5" />
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* 控制栏 */}
        <div className="mt-4 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            {/* 幻灯片指示器 */}
            {promotions.length > 1 && (
              <div className="flex space-x-2">
                {promotions.map((_, index) => (
                  <button
                    key={index}
                    onClick={() => goToSlide(index)}
                    className={`w-3 h-3 rounded-full transition-colors ${
                      index === currentSlide ? 'bg-blue-600' : 'bg-gray-300 hover:bg-gray-400'
                    }`}
                  />
                ))}
              </div>
            )}
            
            {/* 幻灯片计数 */}
            <span className="text-sm text-gray-600">
              {currentSlide + 1} / {promotions.length}
            </span>
          </div>

          <div className="flex items-center space-x-3">
            {/* 自动播放控制 */}
            {promotions.length > 1 && (
              <button
                onClick={toggleAutoPlay}
                className={`flex items-center space-x-1 px-3 py-1 rounded text-sm transition-colors ${
                  isAutoPlay ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
                }`}
              >
                {isAutoPlay ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                <span>{isAutoPlay ? 'Auto' : 'Manual'}</span>
              </button>
            )}

            {/* 管理按钮 */}
            <button
              onClick={() => setViewMode('manage')}
              className="px-3 py-1 bg-gray-600 text-white rounded text-sm hover:bg-gray-700 transition-colors"
            >
              Manage
            </button>
          </div>
        </div>
      </div>
    );
  };

  // 管理模式渲染
  const renderManageMode = () => (
    <div className="h-full flex flex-col">
      {/* 头部 */}
      <div className="flex-shrink-0 p-6 border-b">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold text-gray-900">Promotions Management</h2>
          <button
            onClick={() => setViewMode('showcase')}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
          >
            View Showcase
          </button>
        </div>
        
        {/* 上传区域 */}
        <div 
          className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
            dragOver ? 'border-blue-400 bg-blue-50' : 'border-gray-300 bg-gray-50'
          }`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <Upload className="w-8 h-8 mx-auto mb-2 text-gray-500" />
          <p className="text-sm text-gray-600 mb-2">
            Drag and drop promotional images here, or click to upload
          </p>
          <p className="text-xs text-gray-500 mb-3">
            Supports JPG, PNG, GIF, WebP formats, max 10MB per file
          </p>
          <button
            onClick={() => fileInputRef.current?.click()}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
          >
            Choose Files
          </button>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            hidden
            accept="image/*"
            onChange={(e) => handleFileUpload(e.target.files)}
          />
        </div>
      </div>

      {/* 海报列表 */}
      <div className="flex-1 overflow-y-auto p-6">
        {promotions.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <FileImage className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p>No promotional materials uploaded yet</p>
            <p className="text-sm">Upload some images to create a promotional showcase</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {promotions.map((promotion, index) => (
              <div key={promotion.id} className="bg-white border rounded-lg shadow-sm overflow-hidden">
                {/* 图片预览 */}
                <div className="aspect-video bg-gray-100 relative group">
                  <img
                    src={promotion.image}
                    alt={promotion.name}
                    className="w-full h-full object-cover"
                  />
                  <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-50 transition-opacity flex items-center justify-center">
                    <div className="opacity-0 group-hover:opacity-100 transition-opacity flex space-x-2">
                      <button
                        onClick={() => viewFullscreen(promotion)}
                        className="p-2 bg-white text-gray-800 rounded-full hover:bg-gray-100 transition-colors"
                        title="View Fullscreen"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => deletePromotion(promotion.id)}
                        className="p-2 bg-red-600 text-white rounded-full hover:bg-red-700 transition-colors"
                        title="Delete"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                  
                  {/* 当前展示指示器 */}
                  {index === currentSlide && (
                    <div className="absolute top-2 left-2 px-2 py-1 bg-blue-600 text-white text-xs rounded">
                      Currently Showing
                    </div>
                  )}
                </div>

                {/* 信息 */}
                <div className="p-4">
                  <h3 className="font-semibold text-gray-900 mb-2">{promotion.name}</h3>
                  <div className="text-sm text-gray-600 space-y-1">
                    <p>Size: {(promotion.size / 1024 / 1024).toFixed(2)}MB</p>
                    <p>Uploaded: {new Date(promotion.uploadDate).toLocaleDateString()}</p>
                  </div>
                  
                  <div className="mt-3 flex space-x-2">
                    <button
                      onClick={() => {
                        setCurrentSlide(index);
                        setViewMode('showcase');
                      }}
                      className="flex-1 px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 transition-colors"
                    >
                      Show This
                    </button>
                    <button
                      onClick={() => deletePromotion(promotion.id)}
                      className="px-3 py-1 bg-red-600 text-white text-sm rounded hover:bg-red-700 transition-colors"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );

  return (
    <div className="h-full" style={{ backgroundColor: '#fef7e8' }}>
      {viewMode === 'showcase' ? renderShowcaseMode() : renderManageMode()}
    </div>
  );
};

export default PromotionsShowcase;