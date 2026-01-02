import type { FolderInfo } from '../../hooks/usePhotos';

interface FolderLibraryProps {
  folders: FolderInfo[];
  currentPath: string | null;
  onSelectFolder: (path: string) => void;
  onRemoveFolder: (path: string) => void;
  onAddFolder: () => void;
}

export function FolderLibrary({
  folders,
  currentPath,
  onSelectFolder,
  onRemoveFolder,
  onAddFolder,
}: FolderLibraryProps) {
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      year: date.getFullYear() !== new Date().getFullYear() ? 'numeric' : undefined,
    });
  };

  return (
    <div className="w-64 bg-gray-50 dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700 flex flex-col h-full">
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
            Library
          </h2>
          <button
            onClick={onAddFolder}
            className="text-blue-500 hover:text-blue-600 p-1 rounded hover:bg-blue-50 dark:hover:bg-blue-900/20"
            title="Add folder"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {folders.length === 0 ? (
          <div className="p-4 text-center">
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-3">
              No folders in library
            </p>
            <button
              onClick={onAddFolder}
              className="text-sm text-blue-500 hover:text-blue-600"
            >
              Add a folder
            </button>
          </div>
        ) : (
          <ul className="py-2">
            {folders.map((folder) => (
              <li key={folder.path}>
                <button
                  onClick={() => onSelectFolder(folder.path)}
                  className={`w-full text-left px-4 py-2 hover:bg-gray-100 dark:hover:bg-gray-800 group flex items-center gap-2 ${
                    currentPath === folder.path
                      ? 'bg-blue-50 dark:bg-blue-900/30 border-r-2 border-blue-500'
                      : ''
                  }`}
                >
                  <svg
                    className={`w-5 h-5 flex-shrink-0 ${
                      currentPath === folder.path
                        ? 'text-blue-500'
                        : 'text-gray-400 dark:text-gray-500'
                    }`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.5}
                      d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
                    />
                  </svg>
                  <div className="flex-1 min-w-0">
                    <div
                      className={`text-sm font-medium truncate ${
                        currentPath === folder.path
                          ? 'text-blue-600 dark:text-blue-400'
                          : 'text-gray-700 dark:text-gray-300'
                      }`}
                    >
                      {folder.name}
                    </div>
                    <div className="text-xs text-gray-400 dark:text-gray-500 truncate">
                      {formatDate(folder.lastOpenedAt)}
                    </div>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onRemoveFolder(folder.path);
                    }}
                    className="opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-red-500 rounded"
                    title="Remove from library"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
