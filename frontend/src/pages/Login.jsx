import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { authService } from '../lib/api';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    
    try {
      const data = await authService.login(email, password);
      localStorage.setItem('sdr_token', data.access_token);
      navigate('/dashboard');
    } catch (err) {
      setError('Invalid credentials');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col sm:justify-center items-center pt-6 sm:pt-0 bg-slate-50">
      <div className="mb-8 text-center">
        <div className="w-12 h-12 bg-primary-600 rounded-xl mx-auto flex items-center justify-center text-white font-bold text-2xl mb-4 shadow-sm">
          AI
        </div>
        <h1 className="text-3xl font-bold text-slate-900">Welcome back</h1>
        <p className="text-slate-500 mt-2">Sign in to your account</p>
      </div>

      <Card className="w-full sm:max-w-md border-0 shadow-lg sm:rounded-2xl">
        <CardContent className="p-8">
          <div className="mb-6 p-4 bg-blue-50 text-blue-700 rounded-lg text-sm border border-blue-100">
            <span className="font-medium">Note:</span> Please read the documentation for logging in credentials.
          </div>
          <form onSubmit={handleLogin} className="space-y-5">
            {error && (
              <div className="p-3 bg-red-50 text-red-600 rounded-md text-sm">
                {error}
              </div>
            )}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Email address</label>
              <input 
                type="email" 
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full border-slate-300 rounded-lg shadow-sm focus:border-primary-500 focus:ring-primary-500 h-10 px-3 border"
                required
              />
            </div>
            
            <div>
              <div className="flex justify-between mb-1">
                <label className="block text-sm font-medium text-slate-700">Password</label>
                <a href="#" className="text-sm text-primary-600 hover:text-primary-500">Forgot password?</a>
              </div>
              <input 
                type="password" 
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full border-slate-300 rounded-lg shadow-sm focus:border-primary-500 focus:ring-primary-500 h-10 px-3 border"
                required
              />
            </div>
            
            <Button type="submit" className="w-full" size="lg" disabled={loading}>
              {loading ? 'Signing in...' : 'Sign in'}
            </Button>
          </form>
          
          <div className="mt-6">
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-slate-200"></div>
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-2 bg-white text-slate-500">Or continue with</span>
              </div>
            </div>
            
            <div className="mt-6 grid grid-cols-2 gap-3">
              <Button variant="secondary" className="w-full bg-white">
                <img className="h-5 w-5 mr-2" src="https://www.svgrepo.com/show/475656/google-color.svg" alt="Google" />
                Google
              </Button>
              <Button variant="secondary" className="w-full bg-white">
                <img className="h-5 w-5 mr-2" src="https://www.svgrepo.com/show/448234/microsoft.svg" alt="Microsoft" />
                Microsoft
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
