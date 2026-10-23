import { UI_MARKUP } from './uiMarkup';
import { UiScripts } from './UiScripts';

export default function Home() {
  return (
    <>
      <div style={{ display: 'contents' }} suppressHydrationWarning dangerouslySetInnerHTML={{ __html: UI_MARKUP }} />
      <UiScripts />
    </>
  );
}
