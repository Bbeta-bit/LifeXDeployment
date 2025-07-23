import { useTranslation } from 'react-i18next';

export default function LanguageSelector() {
  const { i18n } = useTranslation();

  const handleChange = (e) => {
    i18n.changeLanguage(e.target.value);
  };

  return (
    <select
      onChange={handleChange}
      value={i18n.language}
      className="border border-gray-300 rounded px-2 py-1 text-sm"
    >
      <option value="en">English</option>
      <option value="zh-CN">简体中文</option>
      <option value="zh-TW">繁體中文</option>
      <option value="vi">Tiếng Việt</option>
      <option value="hi">हिन्दी</option>
      <option value="de">Deutsch</option>
      <option value="ko">한국어</option>
      <option value="ja">日本語</option>
    </select>
  );
}


