import React, { useState, useRef, useEffect } from 'react';
import { ChevronLeft, ChevronRight, Play, Pause, FileImage, AlertCircle } from 'lucide-react';

const PromotionsShowcase = () => {
  const [promotions, setPromotions] = useState([]);
  const [currentSlide, setCurrentSlide] = useState(0);
  const [isAutoPlay, setIsAutoPlay] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const autoPlayRef = useRef(null);

  // 从public/promotions文件夹加载海报
  useEffect(() => {
    loadPromotions();
  }, []);

  const loadPromotions = async () => {
    try {
      setLoading(true);
      setError(null);

      // 定义要查找的图片文件名列表
      // 你需要将海报文件放在 public/promotions/ 文件夹中
      const imageFiles = [
        'promotion1.jpg',
        'promotion2.jpg', 
        'promotion3.jpg',
        'promotion4.png',
        'promotion5.png',
        // 可以继续添加更多文件名
      ];

      const loadedPromotions = [];

      // 尝试加载每个图片文件
      for (const filename of imageFiles) {
        try {
          const imagePath = `/promotions/${filename}`;
          
          // 检查图片是否存在
          const response = await fetch(imagePath, { method: 'HEAD' });
          if (response.ok) {
            loadedPromotions.push({
              id: filename,
              name: filename.replace(/\.[^/.]+$/, "").replace(/[-_]/g, ' ').toUpperCase(),
              image: imagePath,
              filename: filename,
              uploadDate: new Date().toISOString() // 可以从文件属性获取真实日期
            });
          }
        } catch (err) {
          // 文件不存在，继续下一个
          console.log(`Promotion file not found: ${filename}`);
        }
      }

      setPromotions(loadedPromotions);
      
      if (loadedPromotions.length === 0) {
        setError('No promotional materials found. Please add image files to the /public/promotions/ folder.');
      }

    } catch (err) {
      console.error('Error loading promotions:', err);
      setError('Failed to load promotional materials.');
    } finally {
      setLoading(false);
    }
  };

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
            body { 
              margin: 0; 
              padding: 20px; 
              background: #000; 
              display: flex; 
              justify-content: center; 
              align-items: center; 
              min-height: 100vh; 
            }
            img { 
              max-width: 100%; 
              max-height: 100%; 
              object-fit: contain; 
              border-radius: 8px;
              box-shadow: 0 4px 20px rgba(255,255,255,0.1);
            }
          </style>
        </head>
        <body>
          <img src="${promotion.image}" alt="${promotion.name}" />
        </body>
      </html>
    `);
  };

  // 加载状态
  if (loading) {
    return (
      <div className="h-full flex items-center justify-center" style={{ backgroundColor: '#fef7e8' }}>
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading promotional materials...</p>
        </div>
      </div>
    );
  }

  // 错误状态
  if (error) {
    return (
      <div className="h-full flex items-center justify-center p-6" style={{ backgroundColor: '#fef7e8' }}>
        <div className="text-center max-w-md">
          <AlertCircle className="w-16 h-16 text-yellow-500 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-gray-800 mb-3">No Promotions Available</h3>
          <p className="text-gray-600 mb-4">{error}</p>
          
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-left">
            <h4 className="font-medium text-blue-800 mb-2">Setup Instructions:</h4>
            <ol className="text-sm text-blue-700 space-y-1">
              <li>1. Create a <code className="bg-blue-200 px-1 rounded">public/promotions/</code> folder in your project</li>
              <li>2. Add your promotional images (JPG, PNG, GIF, WebP)</li>
              <li>3. Name them as: promotion1.jpg, promotion2.png, etc.</li>
              <li>4. Refresh this page to see your promotions</li>
            </ol>
          </div>
          
          <button
            onClick={loadPromotions}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
          >
            Refresh Promotions
          </button>
        </div>
      </div>
    );
  }

  // 空状态（没有找到海报）
  if (promotions.length === 0) {
    return (
      <div className="h-full flex items-center justify-center p-6" style={{ backgroundColor: '#fef7e8' }}>
        <div className="text-center max-w-md">
          <FileImage className="w-20 h-20 text-gray-400 mx-auto mb-6" />
          <h3 className="text-2xl font-bold text-gray-700 mb-3">No Promotional Materials</h3>
          <p className="text-gray-500 mb-6">Add promotional images to the project folder to showcase your latest offers.</p>
          
          <div className="bg-gray-50 border rounded-lg p-4 text-left">
            <h4 className="font-medium text-gray-800 mb-2">How to Add Promotions:</h4>
            <ul className="text-sm text-gray-600 space-y-1">
              <li>• Place images in <code className="bg-gray-200 px-1 rounded">public/promotions/</code></li>
              <li>• Supported formats: JPG, PNG, GIF, WebP</li>
              <li>• File names: promotion1.jpg, promotion2.png, etc.</li>
              <li>• Images will automatically appear here</li>
            </ul>
          </div>

          <button
            onClick={loadPromotions}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
          >
            Check for Promotions
          </button>
        </div>
      </div>
    );
  }

  // 正常展示模式
  const currentPromotion = promotions[currentSlide];

  return (
    <div className="h-full flex flex-col p-6" style={{ backgroundColor: '#fef7e8' }}>
      {/* 标题栏 */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">Current Promotions</h2>
          <p className="text-sm text-gray-600">Latest offers and marketing materials</p>
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-sm text-gray-500">
            {promotions.length} promotion{promotions.length > 1 ? 's' : ''}
          </span>
          <button
            onClick={loadPromotions}
            className="px-3 py-1 text-sm bg-gray-200 text-gray-700 rounded hover:bg-gray-300 transition-colors"
          >
            Refresh
          </button>
        </div>
      </div>

      {/* 主展示区域 */}
      <div className="flex-1 relative bg-white rounded-lg overflow-hidden shadow-lg">
        <img
          src={currentPromotion.image}
          alt={currentPromotion.name}
          className="w-full h-full object-contain bg-gray-50"
          onError={(e) => {
            console.error('Failed to load image:', currentPromotion.image);
            e.target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjMwMCIgdmlld0JveD0iMCAwIDQwMCAzMDAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSI0MDAiIGhlaWdodD0iMzAwIiBmaWxsPSIjRjNGNEY2Ii8+CjxwYXRoIGQ9Im0xNTAgMTUwIDUwIDUwaDEwMGwtNTAtNTB6IiBmaWxsPSIjOUI5QkEwIi8+CjwvU3ZnPgo=';
          }}
        />
        
        {/* 导航按钮 */}
        {promotions.length > 1 && (
          <>
            <button
              onClick={prevSlide}
              className="absolute left-4 top-1/2 transform -translate-y-1/2 bg-black bg-opacity-50 text-white p-3 rounded-full hover:bg-opacity-75 transition-opacity"
            >
              <ChevronLeft className="w-6 h-6" />
            </button>
            <button
              onClick={nextSlide}
              className="absolute right-4 top-1/2 transform -translate-y-1/2 bg-black bg-opacity-50 text-white p-3 rounded-full hover:bg-opacity-75 transition-opacity"
            >
              <ChevronRight className="w-6 h-6" />
            </button>
          </>
        )}

        {/* 信息覆盖层 */}
        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black via-black/70 to-transparent p-6">
          <h3 className="text-white text-xl font-semibold mb-2">{currentPromotion.name}</h3>
          <div className="flex items-center justify-between">
            <p className="text-gray-300 text-sm">
              Promotion {currentSlide + 1} of {promotions.length}
            </p>
            <div className="flex space-x-3">
              <button
                onClick={() => viewFullscreen(currentPromotion)}
                className="px-3 py-1 bg-white/20 text-white text-sm rounded hover:bg-white/30 transition-colors"
              >
                View Fullscreen
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
                  className={`w-3 h-3 rounded-full transition-all duration-200 ${
                    index === currentSlide 
                      ? 'bg-blue-600 scale-125' 
                      : 'bg-gray-300 hover:bg-gray-400'
                  }`}
                  title={`Go to promotion ${index + 1}`}
                />
              ))}
            </div>
          )}
          
          {/* 当前幻灯片信息 */}
          <div className="text-sm text-gray-600">
            <span className="font-medium">{currentPromotion.filename}</span>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          {/* 自动播放控制 */}
          {promotions.length > 1 && (
            <button
              onClick={toggleAutoPlay}
              className={`flex items-center space-x-2 px-3 py-1 rounded text-sm transition-colors ${
                isAutoPlay ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
              }`}
            >
              {isAutoPlay ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
              <span>{isAutoPlay ? 'Auto Playing' : 'Paused'}</span>
            </button>
          )}

          {/* 刷新按钮 */}
          <button
            onClick={loadPromotions}
            className="px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 transition-colors"
          >
            Refresh
          </button>
        </div>
      </div>

      {/* 海报缩略图列表 */}
      {promotions.length > 1 && (
        <div className="mt-4 pt-4 border-t">
          <div className="flex space-x-3 overflow-x-auto pb-2">
            {promotions.map((promo, index) => (
              <button
                key={promo.id}
                onClick={() => goToSlide(index)}
                className={`flex-shrink-0 relative ${
                  index === currentSlide ? 'ring-2 ring-blue-600' : 'ring-1 ring-gray-200'
                } rounded-lg overflow-hidden transition-all duration-200 hover:ring-2 hover:ring-blue-400`}
              >
                <img
                  src={promo.image}
                  alt={promo.name}
                  className="w-20 h-16 object-cover"
                />
                {index === currentSlide && (
                  <div className="absolute inset-0 bg-blue-600/20 flex items-center justify-center">
                    <div className="w-3 h-3 bg-blue-600 rounded-full"></div>
                  </div>
                )}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* 管理提示 */}
      <div className="mt-4 p-3 bg-blue-50 rounded-lg border border-blue-200">
        <p className="text-xs text-blue-700">
          <strong>For Administrators:</strong> To update promotional materials, add or replace image files in the 
          <code className="bg-blue-200 px-1 rounded mx-1">public/promotions/</code> 
          folder and click "Refresh". Supported formats: JPG, PNG, GIF, WebP.
        </p>
      </div>
    </div>
  );
};

export default PromotionsShowcase;