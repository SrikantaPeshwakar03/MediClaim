import { Link, useLocation } from 'react-router-dom';
import { Activity, FileText, CheckCircle } from 'lucide-react';

/**
 * Layout component with enhanced header and main content area
 */
export default function Layout({ children }) {
  const location = useLocation();
  
  const getPageInfo = () => {
    if (location.pathname === '/') return { title: 'Submit Claim', icon: FileText };
    if (location.pathname.includes('/status')) return { title: 'Claim Status', icon: Activity };
    if (location.pathname.includes('/decision')) return { title: 'Claim Decision', icon: CheckCircle };
    return { title: '', icon: null };
  };

  const { title, icon: Icon } = getPageInfo();
  
  return (
    <div className="min-h-screen">
      <header className="bg-white/80 backdrop-blur-md shadow-sm border-b border-gray-200/50 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <Link to="/" className="flex items-center gap-2 group">
              <div className="bg-gradient-to-r from-blue-600 to-indigo-600 p-2 rounded-lg group-hover:shadow-lg transition-shadow">
                <Activity className="h-6 w-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
                  MediClaim AI
                </h1>
                <p className="text-xs text-gray-500">Intelligent Claims Processing</p>
              </div>
            </Link>
            {Icon && (
              <div className="flex items-center gap-2 text-gray-600">
                <Icon className="h-5 w-5" />
                <span className="text-sm font-medium">{title}</span>
              </div>
            )}
          </div>
        </div>
      </header>
      
      <main className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        {children}
      </main>
      
      <footer className="mt-16 border-t border-gray-200/50 bg-white/50 backdrop-blur-sm no-print">
        <div className="max-w-7xl mx-auto px-4 py-6 text-center text-sm text-gray-600">
          <p className="font-medium">MediClaim AI - Health Insurance Claims Processing System</p>
          <p className="mt-1 text-xs">Powered by LangGraph Multi-Agent Architecture • Every decision explainable</p>
        </div>
      </footer>
    </div>
  );
}
