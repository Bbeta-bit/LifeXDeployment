import React, { useState, useEffect } from 'react';
import { X, Info, DollarSign, Calendar, FileText, AlertCircle } from 'lucide-react';

const ProductComparison = ({ recommendations = [], onRecommendationUpdate }) => {
  const [storedRecommendations, setStoredRecommendations] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [showModal, setShowModal] = useState(false);

  // 管理推荐产品存储，最多保留3个最新的
  useEffect(() => {
    if (recommendations && recommendations.length > 0) {
      const newRecommendations = recommendations.map(rec => ({
        ...rec,
        id: `${rec.lender_name}_${rec.product_name}_${Date.now()}`,
        timestamp: new Date().toISOString()
      }));

      setStoredRecommendations(prev => {
        const updated = [...newRecommendations, ...prev];
        // 去重，基于lender_name和product_name
        const unique = updated.filter((item, index, self) => 
          index === self.findIndex(t => 
            t.lender_name === item.lender_name && t.product_name === item.product_name
          )
        );
        // 只保留最新的3个
        return unique.slice(0, 3);
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

  // 单个产品详细视图
  const renderSingleProduct = (product) => (
    <div className="p-6 space-y-6">
      <div className="border-b pb-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-xl font-bold text-gray-900">
              {product.lender_name} - {product.product_name}
            </h3>
            <p className="text-sm text-gray-500 mt-1">
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

  // 比较表格视图
  const renderComparisonTable = () => (
    <div className="p-6">
      <div className="border-b pb-4 mb-6">
        <div className="flex items-center justify-between">
          <h3 className="text-xl font-bold text-gray-900">Product Comparison</h3>
          <button
            onClick={clearRecommendations}
            className="text-sm text-red-600 hover:text-red-800 px-3 py-1 border border-red-200 rounded hover:bg-red-50"
          >
            Clear All
          </button>
        </div>
        <p className="text-sm text-gray-600 mt-1">
          Comparing {storedRecommendations.length} loan products
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full border-collapse border border-gray-300">
          <thead className="bg-gray-50">
            <tr>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-700">
                Lender & Product
              </th>
              <th className="border border-gray-300 px-4 py-3 text-center font-semibold text-gray-700">
                Interest Rate
              </th>
              <th className="border border-gray-300 px-4 py-3 text-center font-semibold text-gray-700">
                Comparison Rate
              </th>
              <th className="border border-gray-300 px-4 py-3 text-center font-semibold text-gray-700">
                Max Loan
              </th>
              <th className="border border-gray-300 px-4 py-3 text-center font-semibold text-gray-700">
                Est. Fee*
              </th>
              <th className="border border-gray-300 px-4 py-3 text-center font-semibold text-gray-700">
                Balloon Available
              </th>
              <th className="border border-gray-300 px-4 py-3 text-center font-semibold text-gray-700">
                Details
              </th>
            </tr>
          </thead>
          <tbody>
            {storedRecommendations.map((product, index) => (
              <tr key={product.id} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                <td className="border border-gray-300 px-4 py-3">
                  <div>
                    <div className="font-semibold text-gray-900">{product.lender_name}</div>
                    <div className="text-sm text-gray-600">{product.product_name}</div>
                    <div className="text-xs text-gray-500 mt-1">
                      Added {new Date(product.timestamp).toLocaleDateString()}
                    </div>
                  </div>
                </td>
                <td className="border border-gray-300 px-4 py-3 text-center">
                  <div className="text-lg font-bold text-blue-600">
                    {product.base_rate}%
                  </div>
                </td>
                <td className="border border-gray-300 px-4 py-3 text-center">
                  <div className="text-sm font-medium">
                    {product.comparison_rate ? `${product.comparison_rate}%` : 'N/A'}
                  </div>
                </td>
                <td className="border border-gray-300 px-4 py-3 text-center">
                  <div className="text-sm font-medium">
                    {product.max_loan_amount}
                  </div>
                </td>
                <td className="border border-gray-300 px-4 py-3 text-center">
                  <div className="text-sm">
                    {product.fees_breakdown?.establishment_fee || 'See details'}
                  </div>
                </td>
                <td className="border border-gray-300 px-4 py-3 text-center">
                  <div className="text-sm">
                    {product.rate_conditions?.balloon_options ? '✓ Yes' : '✗ No'}
                  </div>
                </td>
                <td className="border border-gray-300 px-4 py-3 text-center">
                  <button
                    onClick={() => handleProductClick(product)}
                    className="inline-flex items-center px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 transition-colors"
                  >
                    <Info className="w-4 h-4 mr-1" />
                    View
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-4 text-xs text-gray-500">
        * Establishment fees shown where available. Additional fees may apply. Click "View" for complete fee breakdown.
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
        {/* 根据推荐数量渲染不同视图 */}
        {storedRecommendations.length === 0 && renderEmptyState()}
        {storedRecommendations.length === 1 && renderSingleProduct(storedRecommendations[0])}
        {storedRecommendations.length > 1 && renderComparisonTable()}
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
              <h2 className="text-xl font-bold text-gray-900">
                {selectedProduct.lender_name} - {selectedProduct.product_name}
              </h2>
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