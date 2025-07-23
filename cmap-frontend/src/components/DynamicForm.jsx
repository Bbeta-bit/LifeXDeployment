import React from 'react';

export default function DynamicForm({ schema, formData, onChange }) {
  if (!schema || !schema.fields) {
    return <div className="p-4 text-gray-500">Loading form...</div>;
  }

  const handleChange = (fieldName, value) => {
    onChange({ ...formData, [fieldName]: value });
  };

  return (
    <form className="p-6 space-y-6 bg-white shadow rounded-lg">
      {schema.fields.map((field) => {
        const { name, label, type, options, required } = field;

        return (
          <div key={name}>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {label}{required && <span className="text-red-500 ml-1">*</span>}
            </label>

            {type === 'text' && (
              <input
                type="text"
                value={formData[name] || ''}
                onChange={(e) => handleChange(name, e.target.value)}
                className="block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 p-2 border"
                required={required}
              />
            )}

            {type === 'select' && (
              <select
                value={formData[name] || ''}
                onChange={(e) => handleChange(name, e.target.value)}
                className="block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 p-2 border"
                required={required}
              >
                <option value="">-- Select --</option>
                {options.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            )}
          </div>
        );
      })}
    </form>
  );
}
