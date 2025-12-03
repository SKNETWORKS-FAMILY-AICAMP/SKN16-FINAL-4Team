import React, { useState, useRef } from 'react';
import { Upload, message, Modal, Image as AntdImage } from 'antd';
import type { GetProp, UploadProps, UploadFile } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import ImgCrop from 'antd-img-crop';
import { uploadImageToS3 } from '@/utils/s3Upload';

type FileType = Parameters<GetProp<UploadProps, 'beforeUpload'>>[0];

interface Props {
    onUpload: (result: { key: string; url?: string }, file: File) => Promise<void> | void;
    maxCount?: number;
    accept?: string;
}

const ImageUploader: React.FC<Props> = ({ onUpload, maxCount = 1, accept = 'image/*' }) => {
    const [previewOpen, setPreviewOpen] = useState(false);
    const [previewImage, setPreviewImage] = useState('');
    const [fileList, setFileList] = useState<UploadFile[]>([]);
    const [isUploading, setIsUploading] = useState(false);
    const [progress, setProgress] = useState(0);
    const progressRef = useRef<number | null>(null);
    const [messageApi, contextHolder] = message.useMessage();

    const getBase64 = (file: FileType): Promise<string> =>
        new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.readAsDataURL(file);
            reader.onload = () => resolve(reader.result as string);
            reader.onerror = (error) => reject(error);
        });

    const handleBeforeUpload: UploadProps['beforeUpload'] = async (file, _fileList) => {
        // show uploading placeholder
        const uploadingFile: UploadFile = {
            uid: '-1',
            name: file.name,
            status: 'uploading',
            originFileObj: file,
            url: URL.createObjectURL(file),
        };
        setFileList([uploadingFile]);

        try {
            // start simulated progress
            setIsUploading(true);
            setProgress(6);
            progressRef.current = window.setInterval(() => {
                setProgress((p) => Math.min(80, p + Math.random() * 8));
            }, 400) as unknown as number;

            const up = await uploadImageToS3(file as File);
            // update list with final url if available
            const doneFile: UploadFile = {
                uid: '-1',
                name: file.name,
                status: 'done',
                originFileObj: file,
                url: up.url || URL.createObjectURL(file),
            };
            setProgress(100);
            // ensure interval cleared and finalize
            if (progressRef.current) {
                window.clearInterval(progressRef.current as number);
                progressRef.current = null;
            }
            setTimeout(() => {
                setIsUploading(false);
                setProgress(0);
            }, 400);

            setFileList([doneFile]);
            await onUpload(up, file as File);
        } catch (err) {
            messageApi.error('이미지 업로드 중 오류가 발생했습니다.');
            if (progressRef.current) {
                window.clearInterval(progressRef.current as number);
                progressRef.current = null;
            }
            setIsUploading(false);
            setProgress(0);
            setFileList([]);
        }

        // prevent default auto upload
        return false;
    };

    const handleChange: UploadProps['onChange'] = ({ fileList: newList }) => {
        setFileList(newList as UploadFile[]);
    };

    const handlePreview = async (file: UploadFile) => {
        let src = file.url as string;
        if (!src && !file.preview) {
            file.preview = await getBase64(file.originFileObj as FileType);
        }
        setPreviewImage(file.url || (file.preview as string));
        setPreviewOpen(true);
    };

    const handleRemove = (file: UploadFile) => {
        try {
            if (file.url && file.url.startsWith('blob:')) {
                URL.revokeObjectURL(file.url);
            }
        } catch (e) { }
        setFileList([]);
        return true;
    };

    const uploadButton = (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
            <PlusOutlined style={{ fontSize: 20, color: 'rgba(0,0,0,0.65)' }} />
            <div style={{ fontSize: 12, color: 'rgba(0,0,0,0.6)' }}>{isUploading ? '업로드 중...' : '이미지 업로드'}</div>
            {isUploading && (
                <div style={{ width: 56, height: 6, borderRadius: 6, background: 'rgba(0,0,0,0.06)', marginTop: 6 }}>
                    <div style={{ width: `${Math.max(6, Math.min(100, progress))}%`, height: '100%', background: '#1890ff', borderRadius: 6, transition: 'width 300ms linear' }} />
                </div>
            )}
        </div>
    );

    return (
        <div className="image-uploader-root">
            {contextHolder}
            <ImgCrop rotationSlider>
                <Upload
                    accept={accept}
                    listType="picture-card"
                    fileList={fileList}
                    beforeUpload={handleBeforeUpload}
                    onChange={handleChange}
                    onPreview={handlePreview}
                    onRemove={handleRemove}
                    maxCount={maxCount}
                    itemRender={(originNode: any, file: UploadFile) => {
                        const uploadingItem = isUploading || (file && file.status === 'uploading');
                        return (
                            <div style={{ position: 'relative', width: 96, height: 96, borderRadius: 10, overflow: 'hidden', boxShadow: '0 1px 2px rgba(16,24,40,0.05)', border: '1px solid rgba(0,0,0,0.06)', background: '#fafafa' }}>
                                <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                    {originNode}
                                </div>
                                {uploadingItem && (
                                    <div style={{ position: 'absolute', left: 0, top: 0, right: 0, bottom: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: 'rgba(255,255,255,0.75)' }}>
                                        <div style={{ width: 68, height: 8, borderRadius: 8, background: 'rgba(0,0,0,0.06)', marginTop: 10 }}>
                                            <div style={{ width: `${Math.max(6, Math.min(100, progress))}%`, height: '100%', background: '#1890ff', borderRadius: 8, transition: 'width 300ms linear' }} />
                                        </div>
                                        <div style={{ marginTop: 8, fontSize: 12, color: 'rgba(0,0,0,0.65)' }}>{Math.max(1, Math.floor(progress))}%</div>
                                    </div>
                                )}
                            </div>
                        );
                    }}
                >
                    {fileList.length < maxCount && uploadButton}
                </Upload>
            </ImgCrop>
            <Modal open={previewOpen} footer={null} onCancel={() => setPreviewOpen(false)} closable={true} centered>
                <div style={{ textAlign: 'center' }}>
                    <AntdImage preview={false} src={previewImage} alt="preview" style={{ maxWidth: '100%', maxHeight: '80vh' }} />
                </div>
            </Modal>
        </div>
    );
};

export default ImageUploader;
