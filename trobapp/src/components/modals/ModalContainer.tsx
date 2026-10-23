'use client';

import React from 'react';
import { FilterModal } from './FilterModal';
import { CallModal } from './CallModal';
import { SpecModal } from './SpecModal';
import { CompareModal } from './CompareModal';
import { GalleryModal } from './GalleryModal';
import { ReportModal } from './ReportModal';
import { StoreModal } from './StoreModal';
import { AccountModal } from './AccountModal';
import { HelpModal } from './HelpModal';

export const ModalContainer: React.FC = () => {
  return (
    <>
      <FilterModal />
      <CallModal />
      <SpecModal />
      <CompareModal />
      <GalleryModal />
      <ReportModal />
      <StoreModal />
      <AccountModal />
      <HelpModal />
    </>
  );
};
