'use client';

import React from 'react';
import { useApp } from '../../context/AppContext';
import { Header } from '../../components/common/Header';
import { ListView } from '../../components/views/ListView';
import { MapView } from '../../components/views/MapView';
import { InquiriesView } from '../../components/views/InquiriesView';
import { AgentView } from '../../components/views/AgentView';

export default function Home() {
  const { view, isTopCollapsed } = useApp();

  const dataViewAttr = view === 'inqs' ? 'inq' : view;

  return (
    <div
      className={`app ${isTopCollapsed ? 'top-min' : ''}`}
      data-view={dataViewAttr}
    >
      <Header />
      <ListView />
      <MapView />
      <InquiriesView />
      <AgentView />
    </div>
  );
}
