import React, { useState, useEffect } from 'react';
import { X, Info, DollarSign, Calendar, FileText, AlertCircle } from 'lucide-react';

const ProductComparison = ({ recommendations = [], onRecommendationUpdate }) => {
  const [storedRecommendations, setStoredRecommendations] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [showModal, setShowModal] = useState(false);

  // 🔧 管理推荐产品存储，支持最新2个推荐的显示和标记
  useEffect(() => {
    if (recommendations && recommendations.length > 0) {
      console.log('📋 ProductComparison received recommendations:', recommendations);
      
      const newRecommendations = recommendations.map((rec, index) => ({
        ...rec,
        id: `${rec.lender_name}_${rec.product_name}_${Date.now()}_${index}`,
        timestamp: new Date().toISOString(),
        // 🔧 使用recommendation_status字段来标记当前和之前的推荐
        status_label: rec.recommendation_status === 'current' ? 'Current Recommendation' : 
                     rec.recommendation_status === 'previous' ? 'Previous Recommendation' : 
                     index === 0 ? 'Current Recommendation' : 'Previous Recommendation'
      }));

      setStoredRecommendations(prev => {
        // 🔧 新的推荐管理逻辑：保留最新2个，正确标记状态
        const combined = [...newRecommendations, ...prev];
        
        // 去重，基于lender_name和product_name
        const unique = combined.filter((item, index, self) => 
          index === self.findIndex(t => 
            t.lender_name === item.lender_name && t.product_name === item.product_name
          )
        );
        
        // 只保留最新的2个
        const latest = unique.slice(0, 2);
        
        // 🔧 重新标记状态：第一个是Current，第二个是Previous
        return latest.map((rec, index) => ({
          ...rec,
          status_label: index === 0 ? 'Current Recommendation' : 'Previous Recommendation',
          display_order: index + 1
        }));
      });
    }
  }, [recommendations]);

  const handleProductClick = (product) => {
    setSelectedProduct(product);
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
    setSelectedProduct(null);
  };

  const clearRecommendations = () => {
    setStoredRecommendations([]);
    if (onRecommendationUpdate) {
      onRecommendationUpdate([]);
    }
  };

  // 🔧 优化单个产品详细视图，添加状态标记
  const renderSingleProduct = (product) => (
    <div className="p-6 space-y-6">
      <div className="border-b pb-4">
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <h3 className="text-xl font-bold text-gray-900">
                {product.lender_name} - {product.product_name}
              </h3>
              {/* 🔧 状态标记 */}
              <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                product.status_label === 'Current Recommendation' 
                  ? 'bg-green-100 text-green-800' 
                  : 'bg-gray-100 text-gray-700'
              }`}>
                {product.status_label}
              </span>
            </div>
            <p className="text-sm text-gray-500">
              Added {new Date(product.timestamp).toLocaleDateString()} at {new Date(product.timestamp).toLocaleTimeString()}
            </p>
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold text-blue-600">
              {product.base_rate}% p.a.
            </div>
            {product.comparison_rate && (
              <div className="text-sm text-gray-600">
                Comparison: {product.comparison_rate}%
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 核心贷款信息 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-blue-50 p-4 rounded-lg">
          <h4 className="font-semibold text-blue-800 mb-2 flex items-center">
            <DollarSign className="w-4 h-4 mr-1" />
            Loan Details
          </h4>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span>Interest Rate:</span>
              <span className="font-medium">{product.base_rate}% p.a.</span>
            </div>
            {product.comparison_rate && (
              <div className="flex justify-between">
                <span>Comparison Rate:</span>
                <span className="font-medium">{product.comparison_rate}% p.a.</span>
              </div>
            )}
            <div className="flex justify-between">
              <span>Max Loan Amount:</span>
              <span className="font-medium">{product.max_loan_amount}</span>
            </div>
            <div className="flex justify-between">
              <span>Loan Terms:</span>
              <span className="font-medium">{product.loan_term_options}</span>
            </div>
            {product.monthly_payment && (
              <div className="flex justify-between">
                <span>Est. Monthly Payment:</span>
                <span className="font-medium text-green-600">${product.monthly_payment}</span>
              </div>
            )}
          </div>
        </div>

        <div className="bg-green-50 p-4 rounded-lg">
          <h4 className="font-semibold text-green-800 mb-2 flex items-center">
            <FileText className="w-4 h-4 mr-1" />
            Documentation
          </h4>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span>Doc Type:</span>
              <span className="font-medium">{product.documentation_type}</span>
            </div>
            <div className="flex justify-between">
              <span>Requirements Met:</span>
              <span className={`font-medium ${product.requirements_met ? 'text-green-600' : 'text-red-600'}`}>
                {product.requirements_met ? '✓ Yes' : '✗ No'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* 详细要求 */}
      {product.detailed_requirements && (
        <div className="bg-gray-50 p-4 rounded-lg">
          <h4 className="font-semibold text-gray-800 mb-3">Eligibility Requirements</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
            {Object.entries(product.detailed_requirements).map(([key, value]) => (
              <div key={key} className="flex justify-between">
                <span className="text-gray-600 capitalize">{key.replace(/_/g, ' ')}:</span>
                <span className="font-medium text-right ml-2">{value}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 费用明细 */}
      {product.fees_breakdown && (
        <div className="bg-yellow-50 p-4 rounded-lg">
          <h4 className="font-semibold text-yellow-800 mb-3">Fees Breakdown</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
            {Object.entries(product.fees_breakdown).map(([key, value]) => (
              <div key={key} className="flex justify-between">
                <span className="text-gray-600 capitalize">{key.replace(/_/g, ' ')}:</span>
                <span className="font-medium">{value}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 利率条件 */}
      {product.rate_conditions && (
        <div className="bg-purple-50 p-4 rounded-lg">
          <h4 className="font-semibold text-purple-800 mb-3">Rate Conditions</h4>
          <div className="space-y-2 text-sm">
            {Object.entries(product.rate_conditions).map(([key, value]) => (
              <div key={key}>
                <span className="text-gray-600 capitalize font-medium">{key.replace(/_/g, ' ')}:</span>
                <span className="ml-2 text-gray-800">{value}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 文档要求 */}
      {product.documentation_requirements && (
        <div className="bg-indigo-50 p-4 rounded-lg">
          <h4 className="font-semibold text-indigo-800 mb-3">Documentation Required</h4>
          <ul className="list-disc list-inside space-y-1 text-sm">
            {product.documentation_requirements.map((req, index) => (
              <li key={index} className="text-gray-700">{req}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );

  // 🔧 优化两个推荐的并排显示
  const renderTwoRecommendations = () => (
    <div className="p-6 space-y-6">
      <div className="border-b pb-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-xl font-bold text-gray-900">Product Recommendations</h3>
            <p className="text-sm text-gray-600 mt-1">
              Comparing your current and previous recommendations
            </p>
          </div>
          <button
            onClick={clearRecommendations}
            className="text-sm text-red-600 hover:text-red-800 px-3 py-1 border border-red-200 rounded hover:bg-red-50"
          >
            Clear All
          </button>
        </div>
      </div>

      {/* 🔧 垂直排列的推荐显示 */}
      <div className="space-y-6">
        {storedRecommendations.map((product, index) => (
          <div
            key={product.id}
            className={`border rounded-lg p-6 hover:shadow-md transition-shadow ${
              product.status_label === 'Current Recommendation' ? 'border-green-300 bg-green-50' : 'border-gray-200 bg-white'
            }`}
          >
            {/* 产品头部 */}
            <div className="flex justify-between items-start mb-4">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <h4 className="text-lg font-semibold text-gray-900">
                    {product.lender_name} - {product.product_name}
                  </h4>
                  <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                    product.status_label === 'Current Recommendation' 
                      ? 'bg-green-100 text-green-800' 
                      : 'bg-gray-100 text-gray-700'
                  }`}>
                    {product.status_label}
                  </span>
                </div>
                <p className="text-sm text-gray-500">
                  Added {new Date(product.timestamp).toLocaleDateString()}
                </p>
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold text-blue-600">
                  {product.base_rate}% p.a.
                </div>
                {product.comparison_rate && (
                  <div className="text-sm text-gray-600">
                    Comparison: {product.comparison_rate}%
                  </div>
                )}
              </div>
            </div>

            {/* 核心信息网格 */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4 text-sm">
              <div className="flex flex-col">
                <span className="text-gray-600 mb-1">Max Loan:</span>
                <span className="font-medium">{product.max_loan_amount}</span>
              </div>
              <div className="flex flex-col">
                <span className="text-gray-600 mb-1">Terms:</span>
                <span className="font-medium">{product.loan_term_options}</span>
              </div>
              <div className="flex flex-col">
                <span className="text-gray-600 mb-1">Monthly Payment:</span>
                <span className="font-medium text-green-600">
                  {product.monthly_payment ? `$${product.monthly_payment}` : 'See details'}
                </span>
              </div>
              <div className="flex flex-col">
                <span className="text-gray-600 mb-1">Documentation:</span>
                <span className="font-medium">{product.documentation_type}</span>
              </div>
            </div>

            {/* 操作按钮 */}
            <div className="flex justify-end">
              <button
                onClick={() => handleProductClick(product)}
                className="inline-flex items-center px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 transition-colors"
              >
                <Info className="w-4 h-4 mr-1" />
                View Details
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* 比较提示 */}
      <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
        <h4 className="font-medium text-blue-800 mb-2">💡 Comparison Tip</h4>
        <p className="text-sm text-blue-700">
          Your current recommendation reflects your latest requirements. Compare the key differences to see how adjustments impact your loan terms.
        </p>
      </div>
    </div>
  );

  // 空状态
  const renderEmptyState = () => (
    <div className="p-6 text-center">
      <div className="max-w-sm mx-auto">
        <AlertCircle className="w-16 h-16 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-gray-900 mb-2">No Recommendations Yet</h3>
        <p className="text-gray-600 text-sm">
          Product recommendations from your chat conversation will appear here for easy comparison.
        </p>
        <p className="text-gray-500 text-xs mt-2">
          Ask the chatbot about loan options to get started!
        </p>
      </div>
    </div>
  );

  return (
    <>
      <div className="h-full flex flex-col" style={{ backgroundColor: '#fef7e8' }}>
        {/* 🔧 根据推荐数量渲染不同视图 */}
        {storedRecommendations.length === 0 && renderEmptyState()}
        {storedRecommendations.length === 1 && renderSingleProduct(storedRecommendations[0])}
        {storedRecommendations.length >= 2 && renderTwoRecommendations()}
      </div>

      {/* 详细信息弹窗 */}
      {showModal && selectedProduct && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div 
            className="bg-white rounded-lg max-w-4xl max-h-[90vh] w-full overflow-hidden flex flex-col"
            style={{ backgroundColor: '#fef7e8' }}
          >
            {/* 弹窗头部 */}
            <div className="flex items-center justify-between p-4 border-b">
              <div className="flex items-center gap-3">
                <h2 className="text-xl font-bold text-gray-900">
                  {selectedProduct.lender_name} - {selectedProduct.product_name}
                </h2>
                <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                  selectedProduct.status_label === 'Current Recommendation' 
                    ? 'bg-green-100 text-green-800' 
                    : 'bg-gray-100 text-gray-700'
                }`}>
                  {selectedProduct.status_label}
                </span>
              </div>
              <button
                onClick={closeModal}
                className="p-2 hover:bg-gray-100 rounded-full transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* 弹窗内容 */}
            <div className="flex-1 overflow-y-auto">
              {renderSingleProduct(selectedProduct)}
            </div>

            {/* 弹窗底部 */}
            <div className="p-4 border-t bg-gray-50">
              <div className="flex justify-end">
                <button
                  onClick={closeModal}
                  className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700 transition-colors"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default ProductComparison;