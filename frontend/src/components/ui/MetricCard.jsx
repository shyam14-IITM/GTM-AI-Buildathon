import React from 'react';
import { Card, CardContent } from './Card';
import { cn } from '../../lib/utils';

export function MetricCard({ title, value, change, icon: Icon, trend = 'up' }) {
  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-slate-500 mb-1">{title}</p>
            <h4 className="text-3xl font-bold text-slate-900">{value}</h4>
          </div>
          {Icon && (
            <div className="w-12 h-12 bg-primary-50 rounded-xl flex items-center justify-center text-primary-600">
              <Icon className="w-6 h-6" />
            </div>
          )}
        </div>
        {change && (
          <div className="mt-4 flex items-center text-sm">
            <span className={cn(
              "font-medium",
              trend === 'up' ? "text-green-600" : "text-red-600"
            )}>
              {trend === 'up' ? '+' : '-'}{change}%
            </span>
            <span className="text-slate-500 ml-2">from last month</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
